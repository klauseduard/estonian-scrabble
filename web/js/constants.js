/**
 * Game constants — premium square positions and letter data.
 * Ported from game/constants.py.
 */

/** @type {Record<string, {count: number, points: number}>} */
export const LETTER_DISTRIBUTION = {
  a: { count: 10, points: 1 },
  e: { count: 9, points: 1 },
  i: { count: 9, points: 1 },
  o: { count: 5, points: 1 },
  u: { count: 5, points: 1 },
  s: { count: 8, points: 1 },
  t: { count: 7, points: 1 },
  k: { count: 5, points: 1 },
  l: { count: 5, points: 1 },
  d: { count: 4, points: 2 },
  m: { count: 4, points: 2 },
  n: { count: 4, points: 2 },
  r: { count: 2, points: 2 },
  g: { count: 2, points: 3 },
  v: { count: 2, points: 3 },
  b: { count: 1, points: 4 },
  h: { count: 2, points: 4 },
  j: { count: 2, points: 4 },
  p: { count: 2, points: 4 },
  "\u00f5": { count: 2, points: 4 },
  "\u00e4": { count: 2, points: 5 },
  "\u00fc": { count: 2, points: 5 },
  "\u00f6": { count: 2, points: 6 },
  f: { count: 1, points: 8 },
  "\u0161": { count: 1, points: 10 },
  z: { count: 1, points: 10 },
  "\u017e": { count: 1, points: 10 },
  _: { count: 2, points: 0 },
};

/**
 * Get point value for a letter.
 * @param {string} letter
 * @returns {number}
 */
export function getLetterPoints(letter) {
  if (!letter || letter === "_") return 0;
  const entry = LETTER_DISTRIBUTION[letter.toLowerCase()];
  return entry ? entry.points : 0;
}

/** All Estonian letters for the blank tile picker. */
export const ESTONIAN_LETTERS = [
  "A", "B", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
  "N", "O", "P", "R", "S", "\u0160", "Z", "\u017d", "T", "U", "V",
  "\u00d5", "\u00c4", "\u00d6", "\u00dc",
];

/** Triple Word Score positions — Set of "row,col" strings. */
export const TRIPLE_WORD_SCORE = new Set([
  "0,0", "0,7", "0,14",
  "7,0", "7,14",
  "14,0", "14,7", "14,14",
]);

/** Double Word Score positions. */
export const DOUBLE_WORD_SCORE = new Set([
  "1,1", "1,13",
  "2,2", "2,12",
  "3,3", "3,11",
  "4,4", "4,10",
  "10,4", "10,10",
  "11,3", "11,11",
  "12,2", "12,12",
  "13,1", "13,13",
  "7,7",
]);

/** Triple Letter Score positions. */
export const TRIPLE_LETTER_SCORE = new Set([
  "1,5", "1,9",
  "5,1", "5,5", "5,9", "5,13",
  "9,1", "9,5", "9,9", "9,13",
  "13,5", "13,9",
]);

/** Double Letter Score positions. */
export const DOUBLE_LETTER_SCORE = new Set([
  "0,3", "0,11",
  "2,6", "2,8",
  "3,0", "3,7", "3,14",
  "6,2", "6,6", "6,8", "6,12",
  "7,3", "7,11",
  "8,2", "8,6", "8,8", "8,12",
  "11,0", "11,7", "11,14",
  "12,6", "12,8",
  "14,3", "14,11",
]);

/**
 * Get the premium type for a board position.
 * @param {number} row
 * @param {number} col
 * @returns {"TW"|"DW"|"TL"|"DL"|null}
 */
export function getPremiumType(row, col) {
  const key = `${row},${col}`;
  if (TRIPLE_WORD_SCORE.has(key)) return "TW";
  if (DOUBLE_WORD_SCORE.has(key)) return "DW";
  if (TRIPLE_LETTER_SCORE.has(key)) return "TL";
  if (DOUBLE_LETTER_SCORE.has(key)) return "DL";
  return null;
}
