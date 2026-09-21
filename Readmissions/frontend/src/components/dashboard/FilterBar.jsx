import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, ListFilter, Activity } from 'lucide-react';

// Post-discharge trend filters. "Needs Attention" is the triage shortcut —
// it unions action_required + deteriorating, the two statuses that call for
// coordinator follow-up.
const TREND_FILTERS = [
  { key: 'All',            label: 'All' },
  { key: 'NeedsAttention', label: 'Needs Attention', active: 'bg-risk-high text-white border-risk-high' },
  { key: 'improving',      label: 'Improving',       active: 'bg-trend-improving text-white border-trend-improving' },
  { key: 'stable',         label: 'Stable',          active: 'bg-risk-low text-white border-risk-low' },
];

export default function FilterBar() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Read current query parameters, supplying defaults
  const search = searchParams.get('search') || '';
  const filter = searchParams.get('filter') || 'All';
  const trend = searchParams.get('trend') || 'All';
  const sort = searchParams.get('sort') || 'score-desc';

  // Helpers to update parameter state 
  const updateParam = (key, value) => {
    const newParams = new URLSearchParams(searchParams);
    if (!value || value === 'All') {
      newParams.delete(key);
    } else {
      newParams.set(key, value);
    }
    setSearchParams(newParams);
  };

  const handleSearchChange = (e) => {
    updateParam('search', e.target.value);
  };

  const handleFilterClick = (band) => {
    updateParam('filter', band);
  };

  const bands = ['All', 'High', 'Medium', 'Low'];

  return (
    <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm mb-6 flex flex-col md:flex-row items-center justify-between gap-4">
      
      {/* Search Input */}
      <div className="relative w-full md:w-auto flex-1 max-w-sm">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search size={18} className="text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search by Patient ID..."
          value={search}
          onChange={handleSearchChange}
          className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ns-navy focus:border-transparent transition-shadow"
        />
      </div>

      {/* Filter and Sort Controls */}
      <div className="flex flex-wrap items-center gap-4 w-full md:w-auto">

        {/* Post-discharge trend pills */}
        <div className="flex items-center space-x-2 border-r pr-4 border-gray-200">
          <Activity size={18} className="text-gray-400 mr-1 hidden md:block" />
          {TREND_FILTERS.map(({ key, label, active }) => {
            const isActive = trend === key || (key === 'All' && !searchParams.get('trend'));
            const cls = isActive
              ? (active || 'bg-ns-navy text-white border-ns-navy')
              : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300';
            return (
              <button
                key={key}
                onClick={() => updateParam('trend', key)}
                className={`px-3 py-2 rounded-full text-sm font-medium border transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-gray-300 whitespace-nowrap ${cls}`}
              >
                {label}
              </button>
            );
          })}
        </div>

        {/* Risk Filter Pills */}
        <div className="flex items-center space-x-2 border-r pr-4 border-gray-200">
          <ListFilter size={18} className="text-gray-400 mr-2 hidden md:block" />
          
          {bands.map(band => {
            const isActive = filter === band || (band === 'All' && !searchParams.get('filter'));
            
            // Derive Colors based on active state and band type
            let activeClass = '';
            if (isActive) {
              if (band === 'High') activeClass = 'bg-risk-high text-white border-risk-high';
              else if (band === 'Medium') activeClass = 'bg-risk-medium text-white border-risk-medium';
              else if (band === 'Low') activeClass = 'bg-risk-low text-white border-risk-low';
              else activeClass = 'bg-ns-navy text-white border-ns-navy'; // For 'All'
            } else {
              activeClass = 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300';
            }

            return (
              <button
                key={band}
                onClick={() => handleFilterClick(band)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-gray-300 ${activeClass}`}
              >
                {band}
              </button>
            );
          })}
        </div>

      </div>
      
    </div>
  );
}
