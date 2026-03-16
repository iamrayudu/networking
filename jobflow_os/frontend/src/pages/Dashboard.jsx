import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import KPIBar from '../components/dashboard/KPIBar'
import AgentsTab from '../components/dashboard/AgentsTab'
import JobsTab from '../components/dashboard/JobsTab'
import ContactsTab from '../components/dashboard/ContactsTab'
import MemorySearch from '../components/dashboard/MemorySearch'
import ReportsTab from '../components/dashboard/ReportsTab'
import LogsTab from '../components/dashboard/LogsTab'

const TABS = ['Overview', 'Agents', 'Jobs', 'Contacts', 'Logs', 'Memory Search', 'Reports']

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('Jobs')
  const [jobs, setJobs] = useState([])
  const [contacts, setContacts] = useState([])
  const [preferences, setPreferences] = useState([])
  const { send } = useWebSocket()

  function refreshAll() {
    fetch('http://localhost:8000/api/jobs/').then(r => r.json()).then(setJobs).catch(() => {})
    fetch('http://localhost:8000/api/memory/contacts').then(r => r.json()).then(setContacts).catch(() => {})
    fetch('http://localhost:8000/api/memory/preferences').then(r => r.json()).then(setPreferences).catch(() => {})
  }

  useEffect(() => { refreshAll() }, [])

  const kpiExtra = {
    jobs: jobs.length,
    enriched: jobs.filter(j => j.status !== 'PENDING').length,
    stories: jobs.filter(j => j.status === 'STORY_READY' || j.status === 'DONE').length,
    contacts: contacts.length,
    sent: contacts.filter(c => c.status === 'SENT').length,
    replied: contacts.filter(c => c.status === 'REPLIED').length,
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50 font-sans">
      {/* Top nav */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
        <div className="w-7 h-7 rounded-lg bg-purple-600 flex items-center justify-center">
          <span className="text-white text-xs font-bold">JF</span>
        </div>
        <span className="font-semibold text-gray-800 text-sm">JobFlow OS</span>
        <div className="flex-1" />
        <Link to="/command" className="text-xs px-3 py-1.5 bg-purple-600 text-white rounded hover:bg-purple-700">
          Command Center
        </Link>
      </div>

      {/* KPI bar */}
      <KPIBar extra={kpiExtra} />

      {/* Tab nav */}
      <div className="bg-white border-b border-gray-200 px-6 flex gap-0">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 text-sm font-medium border-b-2 -mb-px ${
              activeTab === tab
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'Overview' && (
          <div className="p-6">
            <div className="grid grid-cols-2 gap-6">
              {/* Preferences */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="text-sm font-semibold text-gray-700 mb-3">Learned Preferences</div>
                {preferences.length === 0 ? (
                  <div className="text-xs text-gray-400">No preferences learned yet. Run a session to start learning.</div>
                ) : (
                  <div className="space-y-2">
                    {preferences.map(p => (
                      <div key={p.id} className="text-xs">
                        <div className="flex items-center gap-2">
                          <span className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-xs">{p.category}</span>
                          <span className="text-gray-500">conf: {(p.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div className="text-gray-700 mt-0.5 pl-1">{p.rule}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Quick stats */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="text-sm font-semibold text-gray-700 mb-3">Pipeline Funnel</div>
                {[
                  { label: 'Roles loaded', value: kpiExtra.jobs },
                  { label: 'Enriched', value: kpiExtra.enriched },
                  { label: 'Story ready', value: kpiExtra.stories },
                  { label: 'Contacts found', value: kpiExtra.contacts },
                  { label: 'Messages sent', value: kpiExtra.sent },
                  { label: 'Replies', value: kpiExtra.replied },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center gap-2 mb-1">
                    <div className="text-xs text-gray-500 w-32">{label}</div>
                    <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                      <div
                        className="bg-purple-500 h-1.5 rounded-full"
                        style={{ width: `${kpiExtra.jobs ? Math.min(100, (value / kpiExtra.jobs) * 100) : 0}%` }}
                      />
                    </div>
                    <div className="text-xs font-bold text-gray-700 w-6 text-right">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        {activeTab === 'Agents' && <AgentsTab />}
        {activeTab === 'Jobs' && <JobsTab jobs={jobs} onReload={refreshAll} />}
        {activeTab === 'Contacts' && <ContactsTab contacts={contacts} />}
        {activeTab === 'Logs' && <LogsTab />}
        {activeTab === 'Memory Search' && <MemorySearch />}
        {activeTab === 'Reports' && <ReportsTab />}
      </div>
    </div>
  )
}
