/**
 * Check if a string is a palindrome (case‑insensitive, ignoring non‑alphanumerics).
 * @param {string} s
 * @returns {boolean}
 */
function isPalindrome(s) {
  if (typeof s !== 'string') throw new TypeError('Expected a string');
  const cleaned = s.replace(/[^a-z0-9]/gi, '').toLowerCase();
  return cleaned === cleaned.split('').reverse().join('');
}
module.exports = isPalindrome;
