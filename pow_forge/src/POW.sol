// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {IPoW} from "./IPoW.sol";
import {secp256k1, ECCPoint} from "./secp256k1.sol";

contract PoW is IPoW {
    using MessageHashUtils for bytes32;
    using ECDSA for bytes32;
    using {secp256k1.toPublicKey} for uint256;

    address constant MAGIC_NUMBER = 0x8888888888888888888888888888888888888888;

    // problem info
    uint256 public privateKeyA  = block.timestamp;
    uint160 public difficulty = uint160(0x0000FfffFfFffFFfFffFfffFFfFFFffFFFffFfFf);
    uint256 public numSubmissions = 0;

    mapping(uint256 => uint256) _submissionBlocks;

    constructor() {}

    function submit(
        address recipient,
        ECCPoint memory publicKeyB,
        bytes memory signatureAB,
        bytes calldata data
    ) external {
        // Process submition
        address addressAB = publicKeyB
            .ecAdd(privateKeyA.toPublicKey())
            .toAddress();

        // checking, that solution correct
        if ((uint160(addressAB) ^ uint160(MAGIC_NUMBER)) > difficulty) {
            revert BadSolution(
                addressAB,
                address(difficulty ^ uint160(MAGIC_NUMBER))
            );
        }
        emit Submission(addressAB, data);

        // checking, that solver really found privateKeyB
        require(
            addressAB ==
                keccak256(abi.encodePacked(recipient, data))
                    .toEthSignedMessageHash()
                    .recover(signatureAB),
            BadSignature()
        );

        numSubmissions += 1;

        privateKeyA = uint256(
            keccak256(abi.encodePacked(publicKeyB.x, publicKeyB.y))
        );

        emit NewProblem(privateKeyA, difficulty);
    }


}
