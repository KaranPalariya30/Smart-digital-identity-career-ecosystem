require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const LOCAL_RPC_URL = process.env.LOCAL_RPC_URL || "http://127.0.0.1:8545";
const TESTNET_RPC_URL = process.env.TESTNET_RPC_URL || "";
const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY || "";

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 }
    }
  },
  networks: {
    hardhat: {},
    localhost: {
      url: LOCAL_RPC_URL
    },
    // Optional: only used if TESTNET_RPC_URL / DEPLOYER_PRIVATE_KEY are set
    // in .env. Never commit real private keys — see .env.example.
    ...(TESTNET_RPC_URL && DEPLOYER_PRIVATE_KEY
      ? {
          testnet: {
            url: TESTNET_RPC_URL,
            accounts: [DEPLOYER_PRIVATE_KEY]
          }
        }
      : {})
  }
};
