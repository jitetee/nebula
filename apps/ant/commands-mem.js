// Memory commands: /memorize and /forget
const memory = {};

module.exports.memorize = async function(args){
  if(args.length<2){
    console.log('Usage: /memorize <key> <value> …');
    return;
  }
  const key=args[0];
  const val=args.slice(1).join(' ');
  memory[key]=val;
  console.log(`Memorized: ${key} = ${val}`);
};

module.exports.forget = async function(args){
  if(args.length!==1){
    console.log('Usage: /forget <key>');
    return;
  }
  const key=args[0];
  if(memory.hasOwnProperty(key)){
    delete memory[key];
    console.log(`Forgot ${key}`);
  }else{
    console.log(`Key not found: ${key}`);
  }
};

module.exports.get = (key)=>memory[key];
