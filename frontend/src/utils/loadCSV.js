export async function loadCSV(path) {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`Failed to load CSV from ${path}: ${res.status} ${res.statusText}`);
  }
  const text = await res.text();
  
  if (!text || text.trim().length === 0) {
    throw new Error(`CSV file is empty: ${path}`);
  }

  const lines = text.trim().split("\n");
  if (lines.length < 2) {
    throw new Error(`CSV file has no data rows: ${path}`);
  }
  
  const headers = lines[0].split(",").map(h => h.trim());

  return lines.slice(1).map(line => {
    const values = line.split(",").map(v => v.trim());
    return Object.fromEntries(
      headers.map((h, i) => [h, Number(values[i]) || values[i]])
    );
  });
}
