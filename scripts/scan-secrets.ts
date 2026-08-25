import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

interface Finding {
  readonly file: string;
  readonly type: string;
}

const join = (parts: readonly string[]) => parts.join("");
const patterns: ReadonlyArray<{ readonly expression: RegExp; readonly type: string }> = [
  {
    type: "OpenAI credential",
    expression: new RegExp(
      `${join(["s", "k", "-", "p", "r", "o", "j", "-"])}[A-Za-z0-9_-]{16,}`,
      "g"
    )
  },
  {
    type: "OpenAI service credential",
    expression: new RegExp(
      `${join(["s", "k", "-", "s", "v", "c", "a", "c", "c", "t", "-"])}[A-Za-z0-9_-]{16,}`,
      "g"
    )
  },
  {
    type: "OpenAI legacy credential",
    expression: new RegExp(
      `${join(["s", "k", "-"])}(?!(?:proj|svcacct|or-v1|ant)-)[A-Za-z0-9_-]{20,}`,
      "g"
    )
  },
  {
    type: "OpenRouter credential",
    expression: new RegExp(
      `${join(["s", "k", "-", "o", "r", "-", "v", "1", "-"])}[A-Za-z0-9_-]{16,}`,
      "g"
    )
  },
  {
    type: "Anthropic credential",
    expression: new RegExp(`${join(["s", "k", "-", "a", "n", "t", "-"])}[A-Za-z0-9_-]{16,}`, "g")
  },
  {
    type: "Google credential",
    expression: new RegExp(`${join(["A", "I", "z", "a"])}[A-Za-z0-9_-]{30,}`, "g")
  },
  {
    type: "GitHub credential",
    expression: new RegExp(`${join(["g", "h", "p", "_"])}[A-Za-z0-9]{30,}`, "g")
  },
  {
    type: "GitHub fine-grained credential",
    expression: new RegExp(
      `${join(["g", "i", "t", "h", "u", "b", "_", "p", "a", "t", "_"])}[A-Za-z0-9_]{30,}`,
      "g"
    )
  },
  {
    type: "AWS access key",
    expression: new RegExp(`${join(["A", "K", "I", "A"])}[A-Z0-9]{16}`, "g")
  },
  {
    type: "private key material",
    expression: new RegExp(
      join([
        "-",
        "-",
        "-",
        "-",
        "-",
        "B",
        "E",
        "G",
        "I",
        "N",
        " ",
        "P",
        "R",
        "I",
        "V",
        "A",
        "T",
        "E",
        " ",
        "K",
        "E",
        "Y",
        "-",
        "-",
        "-",
        "-",
        "-"
      ]),
      "g"
    )
  }
];
const secretEnvironmentNames = [
  "ANTHROPIC_API_KEY",
  "CADRE_AI_GATEWAY_API_KEY",
  "CADRE_LOCAL_API_KEY",
  "CADRE_PREMIUM_API_KEY",
  "GEMINI_API_KEY",
  "OPENAI_API_KEY",
  "OPENROUTER_API_KEY"
] as const;
const assignmentExpression = new RegExp(
  `^[ \\t]*(?:(?:export[ \\t]+)?(?:${secretEnvironmentNames.join(
    "|"
  )})[ \\t]*=|["']?(?:${secretEnvironmentNames.join("|")})["']?[ \\t]*:)[ \\t]*(.*)$`,
  "gm"
);

function containsCredentialAssignment(text: string): boolean {
  assignmentExpression.lastIndex = 0;

  for (const match of text.matchAll(assignmentExpression)) {
    let value = (match[1] ?? "").trim();
    const quoted = value.match(/^(["'])(.*?)\1\s*,?\s*(?:#.*)?$/);
    if (quoted) {
      value = quoted[2]?.trim() ?? "";
    } else {
      value = value
        .replace(/\s+#.*$/, "")
        .replace(/,$/, "")
        .trim();
    }

    if (
      value &&
      !/^(?:null|undefined|~)$/i.test(value) &&
      !/^(?:process\.env\.|os\.environ\/|\$\{)/.test(value)
    ) {
      return true;
    }
  }

  return false;
}

const output = execFileSync(
  "git",
  ["ls-files", "--cached", "--others", "--exclude-standard", "-z"],
  { encoding: "buffer" }
);
const files = output.toString("utf8").split("\0").filter(Boolean);
const findings: Finding[] = [];

for (const file of files) {
  let contents: Buffer;
  try {
    contents = readFileSync(file);
  } catch {
    continue;
  }

  if (contents.includes(0)) continue;
  const text = contents.toString("utf8");

  for (const pattern of patterns) {
    pattern.expression.lastIndex = 0;
    if (pattern.expression.test(text)) findings.push({ file, type: pattern.type });
  }

  if (containsCredentialAssignment(text)) {
    findings.push({ file, type: "non-empty credential assignment" });
  }
}

if (findings.length > 0) {
  console.error("Potential secrets detected in source-controlled candidate files:");
  for (const finding of findings) {
    console.error(`- ${finding.file} (${finding.type})`);
  }
  process.exit(1);
}

console.log(`Secret scan passed for ${files.length} source-controlled candidate files.`);
