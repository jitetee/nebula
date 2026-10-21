/**
 * Remove all HTML tags from a string.
 * @param {string} html
 * @returns {string}
 */
function stripHtml(html) {
  if (typeof html !== 'string') throw new TypeError('Expected string');
  return html.replace(/<[^>]*>/g, '').trim();
}
module.exports = stripHtml;
