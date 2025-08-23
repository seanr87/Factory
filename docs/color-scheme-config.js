// Rainbow color progression for chronological fields
// Following ROYGBIV spectrum for logical progression

const FACTORY_COLORS = {
  // Factory Status (high-level study lifecycle)
  FACTORY_STATUS: {
    "Initiation": "RED",        // Just started
    "Todo": "ORANGE",           // Ready to begin work  
    "In Progress": "YELLOW",    // Active development
    "Review": "GREEN",          // Under review/validation
    "Network Execution": "BLUE", // Running across network
    "Analysis": "INDIGO",       // Data analysis phase
    "Complete": "PURPLE",       // Finished
    "Blocked": "GRAY"           // Issues/blocked
  },

  // Study Stage (detailed research phases)
  STUDY_STAGE: {
    "Initiation": "RED",                    // Pre-protocol
    "Protocol development": "ORANGE",       // Designing study
    "Data diagnostics": "YELLOW",           // Initial data checks
    "Phenotype development": "GREEN",       // Building cohorts
    "Phenotype evaluation": "BLUE",         // Validating cohorts
    "Analysis specifications": "INDIGO",    // Finalizing analysis plan
    "Network execution": "PURPLE",          // Running study
    "Study diagnostics": "PINK",            // Post-execution checks
    "Evidence synthesis": "GRAY",           // Meta-analysis
    "Results evaluation": "DARK_GRAY"       // Final interpretation
  },

  // Data Partner Status (partner engagement lifecycle)
  PARTNER_STATUS: {
    "Potential": "RED",           // Identified but not contacted
    "Invited": "ORANGE",          // Invitation sent
    "Committed": "YELLOW",        // Agreed to participate
    "Diagnostics Sent": "GREEN",  // Initial package delivered
    "Diagnostics Returned": "BLUE", // Data quality confirmed
    "Package Executed": "INDIGO", // Study package run
    "Results Uploaded": "PURPLE", // Data submitted
    "Complete": "PINK",          // All deliverables done
    "Withdrawn": "GRAY",         // Opted out
    "Blocked": "DARK_GRAY"       // Issues preventing progress
  }
};

// Helper function to create GitHub Project field options with colors
function createColoredOptions(statusType) {
  const colors = FACTORY_COLORS[statusType];
  return Object.entries(colors).map(([name, color]) => ({
    name,
    color,
    description: `${name} status in ${statusType.toLowerCase()} workflow`
  }));
}

// Export configurations for workflow usage
const PROJECT_FIELD_CONFIGS = {
  factoryStatus: {
    name: "Status",
    dataType: "SINGLE_SELECT",
    options: createColoredOptions("FACTORY_STATUS")
  },
  
  studyStage: {
    name: "Stage", 
    dataType: "SINGLE_SELECT",
    options: createColoredOptions("STUDY_STAGE")
  },
  
  partnerStatus: {
    name: "Site Status",
    dataType: "SINGLE_SELECT", 
    options: createColoredOptions("PARTNER_STATUS")
  }
};

module.exports = { FACTORY_COLORS, PROJECT_FIELD_CONFIGS };