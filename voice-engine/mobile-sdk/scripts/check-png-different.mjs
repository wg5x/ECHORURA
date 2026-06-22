#!/usr/bin/env node
import fs from "node:fs";
import zlib from "node:zlib";

const [firstPath, secondPath, thresholdArg] = process.argv.slice(2);
const minDifferentRatio = Number(thresholdArg ?? "0.01");

if (!firstPath || !secondPath) {
  console.error("Usage: check-png-different.mjs <first.png> <second.png> [min-different-ratio]");
  process.exit(2);
}

function decodePng(pngPath) {
  const png = fs.readFileSync(pngPath);
  if (png.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") {
    throw new Error(`Not a PNG file: ${pngPath}`);
  }

  let offset = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  const idatChunks = [];

  while (offset < png.length) {
    const length = png.readUInt32BE(offset);
    const type = png.subarray(offset + 4, offset + 8).toString("ascii");
    const data = png.subarray(offset + 8, offset + 8 + length);
    offset += 12 + length;

    if (type === "IHDR") {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
    } else if (type === "IDAT") {
      idatChunks.push(data);
    } else if (type === "IEND") {
      break;
    }
  }

  if (bitDepth !== 8 || ![2, 6].includes(colorType)) {
    throw new Error(`Unsupported PNG format: bitDepth=${bitDepth} colorType=${colorType}`);
  }

  const channels = colorType === 6 ? 4 : 3;
  const stride = width * channels;
  const inflated = zlib.inflateSync(Buffer.concat(idatChunks));
  const rows = [];
  let inputOffset = 0;

  for (let y = 0; y < height; y += 1) {
    const filter = inflated[inputOffset];
    inputOffset += 1;
    const row = Buffer.from(inflated.subarray(inputOffset, inputOffset + stride));
    inputOffset += stride;
    const previous = rows[y - 1];

    for (let x = 0; x < stride; x += 1) {
      const left = x >= channels ? row[x - channels] : 0;
      const up = previous ? previous[x] : 0;
      const upLeft = previous && x >= channels ? previous[x - channels] : 0;

      if (filter === 1) {
        row[x] = (row[x] + left) & 0xff;
      } else if (filter === 2) {
        row[x] = (row[x] + up) & 0xff;
      } else if (filter === 3) {
        row[x] = (row[x] + Math.floor((left + up) / 2)) & 0xff;
      } else if (filter === 4) {
        const p = left + up - upLeft;
        const pa = Math.abs(p - left);
        const pb = Math.abs(p - up);
        const pc = Math.abs(p - upLeft);
        const predictor = pa <= pb && pa <= pc ? left : pb <= pc ? up : upLeft;
        row[x] = (row[x] + predictor) & 0xff;
      } else if (filter !== 0) {
        throw new Error(`Unsupported PNG filter: ${filter}`);
      }
    }

    rows.push(row);
  }

  return { width, height, channels, rows };
}

const first = decodePng(firstPath);
const second = decodePng(secondPath);

if (first.width !== second.width || first.height !== second.height) {
  console.error(`PNG dimensions differ: ${first.width}x${first.height} vs ${second.width}x${second.height}`);
  process.exit(1);
}

let differentPixels = 0;
const totalPixels = first.width * first.height;

for (let y = 0; y < first.height; y += 1) {
  const firstRow = first.rows[y];
  const secondRow = second.rows[y];
  for (let x = 0; x < first.width; x += 1) {
    const firstOffset = x * first.channels;
    const secondOffset = x * second.channels;
    const redDiff = Math.abs(firstRow[firstOffset] - secondRow[secondOffset]);
    const greenDiff = Math.abs(firstRow[firstOffset + 1] - secondRow[secondOffset + 1]);
    const blueDiff = Math.abs(firstRow[firstOffset + 2] - secondRow[secondOffset + 2]);
    if (redDiff + greenDiff + blueDiff > 30) {
      differentPixels += 1;
    }
  }
}

const ratio = differentPixels / totalPixels;
console.log(JSON.stringify({
  firstPath,
  secondPath,
  width: first.width,
  height: first.height,
  differentRatio: Number(ratio.toFixed(6)),
}));

if (ratio < minDifferentRatio) {
  console.error(`PNGs are too similar: differentRatio=${ratio.toFixed(6)} min=${minDifferentRatio}`);
  process.exit(1);
}
