const fs = require('fs');
const zlib = require('zlib');

const convlog = require('@kobalab/tenhou-log');

const inputPath =
    '../tenhou_mjlogs/2026062700gm-00a9-0000-0b1a0522&tw=0.mjlog';

const outputPath = 'kobalab_output.json';


// .mjlogを読み込む
const compressed = fs.readFileSync(inputPath);

// gzipを展開してXML文字列にする
const xml = zlib.gunzipSync(compressed).toString('utf8');

// 天鳳XML → 電脳麻将形式
const paipu = convlog(
    xml,
    '2026062700gm-00a9-0000-0b1a0522&tw=0'
);

// JSONとして保存
fs.writeFileSync(
    outputPath,
    JSON.stringify(paipu, null, 2),
    'utf8'
);

console.log('変換完了');
console.log('出力:', outputPath);
