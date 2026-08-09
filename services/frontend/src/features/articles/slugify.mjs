export function slugify(value) {
  let out = "";
  for (const ch of String(value ?? "").toLowerCase()) {
    if (/[a-z0-9]/.test(ch)) out += ch;
    else if (" -_/".includes(ch)) out += "-";
  }
  while (out.includes("--")) out = out.replaceAll("--", "-");
  return out.replace(/^-+|-+$/g, "") || "post";
}
