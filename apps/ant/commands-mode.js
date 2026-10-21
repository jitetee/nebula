// Command to set file permission modes
const fs = require('fs');
module.exports = async function setMode(args){
  if(args.length!==1){
    console.log('Usage: /mode <octal>');
    return;
  }
  const mode=parseInt(args[0],8);
  if(isNaN(mode)){
    console.log('Invalid mode');
    return;
  }
  global.file_mode=mode;
  console.log(`File mode set to ${args[0]}`);
};
