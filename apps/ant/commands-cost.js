// Cost tracking command
let totalCost = 0;
module.exports.add = async function(args){
  if(args.length!==1){
    console.log('Usage: /cost <amount>');
    return;
  }
  const amt = parseFloat(args[0]);
  if(isNaN(amt)){console.log('Invalid number');return;}
  totalCost += amt;
  console.log(`Added ${amt.toFixed(2)} – total: ${totalCost.toFixed(2)}`);
};
module.exports.total = () => totalCost;
module.exports.reset = () => {totalCost=0; console.log('Reset cost to 0');};