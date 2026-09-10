// Generate a throwaway testnet-only deployer wallet.
const { ethers } = require("ethers");
const fs = require("fs");
const w = ethers.Wallet.createRandom();
fs.writeFileSync(
  ".deployer.json",
  JSON.stringify({ address: w.address, privateKey: w.privateKey }, null, 2)
);
console.log("DEPLOYER ADDRESS:", w.address);
