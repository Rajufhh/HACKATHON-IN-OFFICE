const requiredTables = [
  "learners",
  "assessments",
  "reviewers",
  "integrity_rules",
  "submissions",
  "similarity_reports",
  "similarity_matches",
  "flags",
  "cases",
  "case_flags",
  "case_assignments",
  "reviewer_conflicts",
  "case_events",
  "evidence_items",
  "case_decisions",
  "decision_evidence",
  "appeals",
  "appeal_evidence",
  "appeal_events",
] as const;

const foreignKeys: Array<[string, string, string, boolean?]> = [
  ["submissions", "learner_id", "learners"],
  ["submissions", "assessment_id", "assessments"],
  ["similarity_reports", "submission_id", "submissions"],
  ["similarity_matches", "report_id", "similarity_reports"],
  ["flags", "submission_id", "submissions"],
  ["flags", "report_id", "similarity_reports"],
  ["flags", "integrity_rule_id", "integrity_rules"],
  ["cases", "learner_id", "learners"],
  ["case_flags", "case_id", "cases"],
  ["case_flags", "flag_id", "flags"],
  ["case_assignments", "case_id", "cases"],
  ["case_assignments", "reviewer_id", "reviewers"],
  ["reviewer_conflicts", "reviewer_id", "reviewers"],
  ["reviewer_conflicts", "case_id", "cases"],
  ["reviewer_conflicts", "reviewed_by", "reviewers", true],
  ["case_events", "case_id", "cases"],
  ["evidence_items", "case_id", "cases"],
  ["case_decisions", "case_id", "cases"],
  ["case_decisions", "reviewer_id", "reviewers"],
  ["decision_evidence", "decision_id", "case_decisions"],
  ["decision_evidence", "evidence_id", "evidence_items"],
  ["appeals", "decision_id", "case_decisions"],
  ["appeals", "learner_id", "learners"],
  ["appeals", "assigned_reviewer_id", "reviewers", true],
  ["appeal_evidence", "appeal_id", "appeals"],
  ["appeal_evidence", "evidence_id", "evidence_items"],
  ["appeal_events", "appeal_id", "appeals"],
];

export interface DatasetPreview {
  rowCounts: Record<string, number>;
  totalRows: number;
  errors: string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function validateDatasetPreview(input: unknown): DatasetPreview {
  const errors: string[] = [];
  const rowCounts: Record<string, number> = {};

  if (!isRecord(input) || !isRecord(input.tables)) {
    return {
      rowCounts,
      totalRows: 0,
      errors: ["Expected the generated data.json format with a tables object."],
    };
  }
  if ("ground_truth" in input || "ground_truth" in input.tables) {
    errors.push("Ground-truth labels are separate evaluation data and cannot be imported as input.");
  }

  const tables = input.tables;
  for (const tableName of requiredTables) {
    if (!Array.isArray(tables[tableName])) {
      errors.push(`Missing table or invalid row list: ${tableName}.`);
      continue;
    }
    rowCounts[tableName] = tables[tableName].length;
  }

  const idsByTable = new Map<string, Set<string>>();
  for (const [tableName, rawRows] of Object.entries(tables)) {
    if (!Array.isArray(rawRows)) {
      continue;
    }
    const ids = new Set<string>();
    for (const [index, rawRow] of rawRows.entries()) {
      if (!isRecord(rawRow)) {
        errors.push(`${tableName}[${index}] must be an object.`);
        continue;
      }
      if (!("id" in rawRow)) {
        errors.push(`${tableName}[${index}] is missing its primary key (id).`);
        continue;
      }
      const id = String(rawRow.id);
      if (ids.has(id)) {
        errors.push(`${tableName} contains duplicate id ${id}.`);
      }
      ids.add(id);
    }
    idsByTable.set(tableName, ids);
  }

  for (const [sourceTable, field, targetTable, optional] of foreignKeys) {
    const sourceRows = tables[sourceTable];
    const targetIds = idsByTable.get(targetTable);
    if (!Array.isArray(sourceRows) || !targetIds) {
      continue;
    }
    for (const [index, rawRow] of sourceRows.entries()) {
      if (!isRecord(rawRow)) {
        continue;
      }
      const foreignId = rawRow[field];
      if (optional && (foreignId === null || foreignId === undefined)) {
        continue;
      }
      if (foreignId === null || foreignId === undefined || !targetIds.has(String(foreignId))) {
        errors.push(`${sourceTable}[${index}].${field} references no ${targetTable} row.`);
      }
    }
  }

  return {
    rowCounts,
    totalRows: Object.values(rowCounts).reduce((total, count) => total + count, 0),
    errors,
  };
}
