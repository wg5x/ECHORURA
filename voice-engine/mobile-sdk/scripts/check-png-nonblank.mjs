#!/usr/bin/env node
import fs from "node:fs";
import zlib from "node:zlib";

const pngPath = process.argv[2];
const minNonWhiteRatio = Number(process.argv[3] ?? "0.02");

if (!pngPath) {
  console.error("Usage: check-png-nonblank.mjs <png-path> [min-non-white-ratio]");
  process.exit(2);
}

const png = fs.readFileSync(pngPath);
const signature = "89504e470d0a1a0a";
if (png.subarray(0, 8).toString("hex") !== signature) {
  console.error(`Not a PNG file: ${pngPath}`);
  process.exit(2);
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
  console.error(`Unsupported PNG format: bitDepth=${bitDepth} colorType=${colorType}`);
  process.exit(2);
}

const channels = colorType === 6 ? 4 : 3;
const bytesPerPixel = channels;
const stride = width * bytesPerPixel;
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
    const left = x >= bytesPerPixel ? row[x - bytesPerPixel] : 0;
    const up = previous ? previous[x] : 0;
    const upLeft = previous && x >= bytesPerPixel ? previous[x - bytesPerPixel] : 0;

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
      console.error(`Unsupported PNG filter: ${filter}`);
      process.exit(2);
    }
  }

  rows.push(row);
}

let nonWhite = 0;
let opaquePixels = 0;

for (const row of rows) {
  for (let x = 0; x < stride; x += bytesPerPixel) {
    const alpha = channels === 4 ? row[x + 3] : 255;
    if (alpha < 16) {
      continue;
    }

    opaquePixels += 1;
    const red = row[x];
    const green = row[x + 1];
    const blue = row[x + 2];
    if (red < 245 || green < 245 || blue < 245) {
      nonWhite += 1;
    }
  }
}

const ratio = opaquePixels === 0 ? 0 : nonWhite / opaquePixels;
console.log(JSON.stringify({
  path: pngPath,
  width,
  height,
  nonWhiteRatio: Number(ratio.toFixed(6)),
}));

if (ratio < minNonWhiteRatio) {
  console.error(`PNG appears blank: nonWhiteRatio=${ratio.toFixed(6)} min=${minNonWhiteRatio}`);
  process.exit(1);
}
