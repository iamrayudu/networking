import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.websocket_manager import ws_manager
from backend.memory.database import init_db
from backend.routers import jobs, agents_router, approvals, memory_router, reports, logs_router
from backend.config import cfg

app = FastAPI(title='JobFlow OS V2')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{cfg['server']['frontend_port']}"],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(jobs.router)
app.include_router(agents_router.router)
app.include_router(approvals.router)
app.include_router(memory_router.router)
app.include_router(reports.router)
app.include_router(logs_router.router)


@app.on_event('startup')
async def startup():
    from backend.core.logging_setup import setup_logging
    setup_logging()
    init_db()
    ws_manager.loop = asyncio.get_event_loop()


@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket):
    conn_id = await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            t = msg.get('type')
            p = msg.get('payload', {})

            from backend.workers.agent_pool import pool

            if t == 'USER_REPLY':
                if p.get('broadcast'):
                    pool.broadcast_instruction(p['message'])
                else:
                    pool.route_user_reply(p['agent_id'], p['message'])
            elif t == 'APPROVE':
                pool.notify_agent(p['agent_id'], 'approve', p)
            elif t == 'EDIT_APPROVE':
                pool.notify_agent(p['agent_id'], 'edit', p)
            elif t == 'SKIP':
                pool.notify_agent(p['agent_id'], 'skip', p)
            elif t == 'PAUSE_AGENT':
                aid = p['agent_id']
                agent = pool.agents.get(aid)
                if agent:
                    agent.pause_flag.set()
                await ws_manager.broadcast('AGENT_STATUS', {
                    'agent_id': aid, 'status': 'paused', 'current_action': 'paused by user'
                })
            elif t == 'RESUME_AGENT':
                aid = p['agent_id']
                agent = pool.agents.get(aid)
                if agent:
                    agent.pause_flag.clear()
                await ws_manager.broadcast('AGENT_STATUS', {
                    'agent_id': aid, 'status': 'running', 'current_action': 'resumed'
                })
            elif t == 'STOP_AGENT':
                aid = p['agent_id']
                agent = pool.agents.get(aid)
                if agent:
                    agent.stop_flag.set()
                    agent.approval_event.set()
                await ws_manager.broadcast('AGENT_STATUS', {
                    'agent_id': aid, 'status': 'idle', 'current_action': 'stopped'
                })
            elif t == 'START_SESSION':
                # If cookies are provided in the payload, inject them before login
                if p.get('li_at') and p.get('li_jsessionid'):
                    from backend.workers.agent_pool import _inject_browser_cookies, _persist_cookies_to_config
                    from backend.config import cfg
                    email = cfg.get('linkedin', {}).get('email', '')
                    if email:
                        _inject_browser_cookies(email, p['li_at'], p['li_jsessionid'])
                        _persist_cookies_to_config(p['li_at'], p['li_jsessionid'])
                        pool.invalidate_session()  # force re-login with fresh cookies
                pool.start_session(p['job_ids'], p.get('standing_instructions', ''))
            elif t == 'STANDING_INSTRUCTION':
                pool.apply_standing_instruction(p['instruction_text'], p.get('scope', 'ALL'))
            elif t == 'REFRESH_COOKIES':
                ok = pool.refresh_cookies(p.get('li_at', ''), p.get('li_jsessionid', ''))
                await ws_manager.broadcast('COOKIE_REFRESH_RESULT', {
                    'success': ok,
                    'message': 'Cookies refreshed — agents resuming.' if ok else 'Cookie refresh failed — check values.',
                })
            elif t == 'CAPTCHA_DETECTED':
                pool.pause_all_agents()
                for aid in pool.agents:
                    await ws_manager.broadcast('AGENT_STATUS', {
                        'agent_id': aid, 'status': 'paused', 'current_action': 'paused — CAPTCHA'
                    })
    except WebSocketDisconnect:
        ws_manager.disconnect(conn_id)
