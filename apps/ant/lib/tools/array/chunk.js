/**
 * Split an array into chunks of a given size.
 * @param {Array} arr - The array to split.
 * @param {number} size - Desired chunk size (defaults to 1).
 * @returns {Array<Array>} Array of chunked arrays.
 */
function chunk(arr, size = 1) {
  if (!Array.isArray(arr)) throw new TypeError('First argument must be an array');
  if (size <= 0) throw new RangeError('Chunk size must be > 0');
  const result = [];
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size));
  }
  return result;
}
module.exports = chunk;
