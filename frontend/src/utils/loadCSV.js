export async function loadCSV(path) {
  const res = await fetch(path);
  const text = await res.text();

  const lines = text.trim().split("\n");
  const headers = lines[0].split(",").map(h => h.trim());

  return lines.slice(1).map(line => {
    const values = line.split(",").map(v => v.trim());
    return Object.fromEntries(
      headers.map((h, i) => [h, Number(values[i]) || values[i]])
    );
  });
}
