// Read the live Sepolia contract's state to prove it deployed and responds.
const { ethers } = require("ethers");
const fs = require("fs");
const art = JSON.parse(fs.readFileSync("out/HumanFundRound.sol/HumanFundRound.json"));
const provider = new ethers.JsonRpcProvider("https://ethereum-sepolia-rpc.publicnode.com");
const addr = "0x1e0Dd67D678bb7Ff269B3945a0A0E501b9727660";
const c = new ethers.Contract(addr, art.abi, provider);
(async () => {
  console.log("issuer:      ", await c.issuer());
  console.log("operator:    ", await c.operator());
  console.log("matchingPool:", (await c.matchingPool()).toString());
  console.log("projectCount:", (await c.projectCount()).toString());
  console.log("finalized:   ", await c.finalized());
})();
