import React, { useEffect, useState } from 'react';
import { Database, ShieldAlert, BookOpen, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { getModelMetrics } from '../api';

export default function About() {
  const [openGlossaryIndex, setOpenGlossaryIndex] = useState(null);

  // The model card is read from the served model rather than written into this
  // page. It previously described a decision tree trained on a diabetes dataset
  // - the project's earlier model - and stayed that way through the switch to
  // MIMIC, because nothing tied the text to the thing doing the scoring.
  const [card, setCard] = useState(null);
  useEffect(() => { getModelMetrics().then(setCard).catch(() => setCard(null)); }, []);

  const toggleAccordion = (index) => {
    setOpenGlossaryIndex(openGlossaryIndex === index ? null : index);
  };

  const glossaryTerms = [
    {
      term: "AUC-ROC",
      definition: "Area Under the Receiver Operating Characteristic Curve. A performance measurement that tells us how much the model is capable of distinguishing between classes. A perfect model scores 1.0, while a random guess scores 0.5."
    },
    {
      term: "Risk Band",
      definition: "A categorization (High, Medium, Low) assigned to a patient based on their numeric risk score. It helps standardize triage protocols."
    },
    {
      term: "Readmission",
      definition: "An event where a patient is discharged from the hospital and is subsequently admitted back to the hospital within a specific timeframe (often 30 days) for the same or a related condition."
    },
    {
      term: "Charlson Comorbidity Index",
      definition: "A method of predicting mortality by classifying or assigning weights to comorbid conditions (e.g., heart disease, respiratory illness)."
    },
    {
      term: "Feature Driver",
      definition: "A clinical variable (like HbA1c levels or prior admissions) that significantly influenced the machine learning model's prediction for a specific patient."
    }
  ];

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-10 animate-in fade-in duration-500 font-sans pb-16">
      
      {/* Header */}
      <div className="border-b border-gray-200 pb-6 text-center">
        <h1 className="text-3xl font-bold text-ns-navy mb-3">About Preventra</h1>
        <p className="text-gray-500 text-lg max-w-2xl mx-auto">
          Preventra is an AI-powered triage assistant designed to identify patients at elevated risk of hospital readmission, permitting proactive clinical interventions.
        </p>
      </div>

      {/* Model Transparency Card */}
      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="bg-ns-navy px-6 py-4 flex items-center space-x-3">
          <Database className="text-white opacity-80" size={24} />
          <h2 className="text-xl font-semibold text-white">Model Card Transparency</h2>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Architecture</h3>
              <p className="text-gray-900 font-medium text-lg">
                {card?.architecture || 'Loading…'}
              </p>
              {card?.trained_at && (
                <p className="text-xs text-gray-400 mt-1">Trained {card.trained_at}</p>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Target Label</h3>
              <div className="flex items-center space-x-2">
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-bold rounded">30-Day Readmission</span>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Training Dataset</h3>
              <p className="text-gray-900">
                {card?.dataset || 'Loading…'}
                {card?.cohort?.index_stays && (
                  <> — <strong>{card.cohort.index_stays.toLocaleString()}</strong> index stays
                  across <strong>{card.cohort.patients.toLocaleString()}</strong> patients.</>
                )}
              </p>
              {card?.cohort?.exclusions && (
                <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                  Excludes {card.cohort.exclusions}.
                </p>
              )}
            </div>
            {card?.auc_roc && (
              <div>
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Measured Performance</h3>
                <p className="text-gray-900">
                  AUC-ROC <strong>{card.auc_roc.toFixed(4)}</strong>, recall{' '}
                  <strong>{card.recall.toFixed(3)}</strong> at a{' '}
                  {(card.prevalence * 100).toFixed(1)}% readmission base rate.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Glossary Section */}
      <section>
        <div className="flex items-center space-x-3 mb-6 px-1">
          <BookOpen className="text-ns-navy" size={24} />
          <h2 className="text-xl font-semibold text-ns-navy">Platform Glossary</h2>
        </div>
        <div className="space-y-3">
          {glossaryTerms.map((item, idx) => {
            const isOpen = openGlossaryIndex === idx;
            return (
              <div 
                key={idx} 
                className="border border-gray-200 rounded-lg bg-white overflow-hidden shadow-sm transition-all"
              >
                <button 
                  onClick={() => toggleAccordion(idx)}
                  className="w-full px-6 py-4 flex items-center justify-between text-left focus:outline-none hover:bg-gray-50 transition"
                >
                  <span className="font-semibold text-gray-800">{item.term}</span>
                  {isOpen ? (
                    <ChevronUp size={20} className="text-gray-400" />
                  ) : (
                    <ChevronDown size={20} className="text-gray-400" />
                  )}
                </button>
                {isOpen && (
                  <div className="px-6 pb-4 pt-1 text-gray-600 bg-gray-50/50 border-t border-gray-100">
                    {item.definition}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Credits block */}
      <section className="text-center pt-8 border-t border-gray-200 mt-12 text-sm text-gray-500">
        <p className="mb-2">Carefully architected by the <span className="font-bold text-gray-700">Preventra Team</span>.</p>
        <a 
          href="https://github.com/umair-denovonet/preventra" 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex items-center space-x-1 text-ns-navy hover:underline font-medium"
        >
          <span>Read Technical Documentation</span>
          <ExternalLink size={14} />
        </a>
      </section>

    </div>
  );
}
