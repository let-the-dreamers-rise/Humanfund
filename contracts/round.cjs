// Execute one real sybil-proof QF round on Sepolia end-to-end and record receipts.
// Deploys a fresh HumanFundRound (identical bytecode to the verified instance) with a
// funded matching pool, runs attested human contributions, fires a forged-attestation
// sybil that reverts on-chain, finalizes, and reads the pool split. Writes
// round-receipts.json with every tx hash so a reviewer can scroll Etherscan.
const { ethers } = require("ethers");
const fs = require("fs");

const RPC = "https://ethereum-sepolia-rpc.publicnode.com";
const art = JSON.parse(fs.readFileSync("out/HumanFundRound.sol/HumanFundRound.json"));
const dep = JSON.parse(fs.readFileSync(".deployer.json"));

const E = (n) => ethers.parseEther(n);
const F = (w) => ethers.formatEther(w);
const link = (h) => `https://sepolia.etherscan.io/tx/${h}`;

// issuer-signed personhood attestation over keccak256(wallet, humanId), raw digest
// (no EIP-191 prefix) to match the contract's ecrecover.
function attest(signer, wallet, humanId) {
  const digest = ethers.solidityPackedKeccak256(["address", "uint256"], [wallet, humanId]);
  const sig = signer.signingKey.sign(digest);
  return { v: sig.v, r: sig.r, s: sig.s };
}

(async () => {
  const provider = new ethers.JsonRpcProvider(RPC);
  const D = new ethers.Wallet(dep.privateKey, provider); // deployer = issuer = operator
  const bal = await provider.getBalance(D.address);
  console.log("deployer", D.address, F(bal), "ETH");
  if (bal < E("0.04")) throw new Error("insufficient balance for the full round");

  // Ephemeral actor wallets (testnet throwaways; only addresses are recorded).
  const mk = () => ethers.Wallet.createRandom().connect(provider);
  const H1 = mk(), H2 = mk(), H3 = mk(), ATK = mk();

  const receipts = { network: "sepolia", rpc: RPC, issuer: D.address, actors: {
    humanA: H1.address, humanB: H2.address, humanC: H3.address, attacker: ATK.address }, txs: {} };

  // 1. Fund actor wallets (value + gas buffer).
  console.log("\n[1] funding actors");
  for (const [w, amt, tag] of [[H1, "0.0016", "fundA"], [H2, "0.0016", "fundB"],
                                [H3, "0.0046", "fundC"], [ATK, "0.0016", "fundATK"]]) {
    const t = await D.sendTransaction({ to: w.address, value: E(amt) });
    await t.wait();
    receipts.txs[tag] = t.hash;
    console.log("   ", tag, "->", w.address, amt, t.hash);
  }

  // 2. Deploy fresh round with a 0.02 ETH matching pool.
  console.log("\n[2] deploying HumanFundRound with 0.02 ETH pool");
  const factory = new ethers.ContractFactory(art.abi, art.bytecode.object, D);
  const c = await factory.deploy(D.address, { value: E("0.02") });
  await c.waitForDeployment();
  const addr = await c.getAddress();
  receipts.contract = addr;
  receipts.txs.deploy = c.deploymentTransaction().hash;
  console.log("   contract", addr, c.deploymentTransaction().hash);

  // 3. Add two projects.
  console.log("\n[3] adding projects");
  let t = await c.addProject("Clean Water Coalition"); await t.wait();
  receipts.txs.addP0 = t.hash; console.log("    P0 Clean Water Coalition", t.hash);
  t = await c.addProject("SybilDAO"); await t.wait();
  receipts.txs.addP1 = t.hash; console.log("    P1 SybilDAO", t.hash);

  // 4. Honest attested contributions. Clean Water: two humans (breadth).
  //    SybilDAO: one human, 4x the money (depth).
  console.log("\n[4] attested human contributions");
  const contribs = [
    { w: H1, hid: 101, pid: 0, amt: "0.001", tag: "contribA", label: "Human A -> Clean Water 0.001" },
    { w: H2, hid: 102, pid: 0, amt: "0.001", tag: "contribB", label: "Human B -> Clean Water 0.001" },
    { w: H3, hid: 103, pid: 1, amt: "0.004", tag: "contribC", label: "Human C -> SybilDAO   0.004" },
  ];
  for (const k of contribs) {
    const a = attest(D, k.w.address, k.hid);
    const cx = c.connect(k.w);
    const tx = await cx.contribute(k.pid, k.hid, a.v, a.r, a.s, { value: E(k.amt) });
    await tx.wait();
    receipts.txs[k.tag] = tx.hash;
    console.log("    OK ", k.label, tx.hash);
  }

  // 5. Sybil attack: attacker forges a second backer for SybilDAO. The attestation is
  //    signed by the attacker (not the issuer), so ecrecover != issuer -> BadAttestation.
  //    Sent with an explicit gasLimit so the reverted tx is mined and visible on-chain.
  console.log("\n[5] sybil attempt (forged attestation, must revert on-chain)");
  const bogus = attest(ATK, ATK.address, 999); // signed by attacker, not issuer
  const data = c.interface.encodeFunctionData("contribute", [1, 999, bogus.v, bogus.r, bogus.s]);
  const stx = await ATK.sendTransaction({ to: addr, data, value: E("0.001"), gasLimit: 150000 });
  let srec;
  try { srec = await stx.wait(); } catch (e) { srec = e.receipt || null; }
  receipts.txs.sybilReverted = stx.hash;
  const status = srec ? srec.status : "unknown";
  console.log("    sybil tx", stx.hash, "status", status, status === 0 ? "(REVERTED as designed)" : "");

  // 6. Finalize -> split the pool by quadratic subsidy.
  console.log("\n[6] finalize");
  t = await c.finalize(); await t.wait();
  receipts.txs.finalize = t.hash;
  console.log("    finalize", t.hash);

  // 7. Read the result.
  console.log("\n[7] result");
  const out = [];
  for (const id of [0, 1]) {
    const p = await c.projects(id);
    const row = { id, name: p.name, sumContrib: F(p.sumContrib), match: F(p.matchAmount) };
    out.push(row);
    console.log(`    P${id} ${p.name.padEnd(24)} raised ${row.sumContrib} ETH -> match ${row.match} ETH`);
  }
  receipts.result = out;
  receipts.finalizedAt = new Date().toISOString();

  fs.writeFileSync("round-receipts.json", JSON.stringify(receipts, null, 2));
  console.log("\nwrote round-receipts.json");
  console.log("contract:", `https://sepolia.etherscan.io/address/${addr}`);
  console.log("sybil (failed):", link(receipts.txs.sybilReverted));
  console.log("finalize:", link(receipts.txs.finalize));
})();
