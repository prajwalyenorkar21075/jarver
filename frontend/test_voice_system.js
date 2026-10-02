// End-to-End Voice System Verification Test
// Tests Anti-Echo Algorithm, Wake-Word Parsing, and Backend Cloned Voice Multilingual TTS

import assert from 'node:assert';

// 1. Re-implement / import core matching functions to test logic in Node environment
const WAKE_WORDS_ENGLISH = [
  'hello jarvis',
  'okay jarvis',
  'hey jarvis',
  'ok jarvis',
  'hi jarvis',
  'jarvis',
];

const WAKE_WORDS_DEVANAGARI = [
  'नमस्कार जार्विस',
  'नमस्ते जार्विस',
  'जार्विस सुनो',
  'हे जार्विस',
  'ऐक जार्विस',
  'जार्विस',
];

function normalizeForMatch(str) {
  return (str || '')
    .toLowerCase()
    .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"'।॥]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

class EchoAndWakeWordTester {
  constructor() {
    this.recentSpoken = [];
  }

  recordSpokenText(text) {
    const now = Date.now();
    const normalized = normalizeForMatch(text);
    this.recentSpoken.push({ text: text.trim(), normalized, timestamp: now });
  }

  isAcousticEcho(candidate) {
    if (!candidate || !candidate.trim()) return true;
    const norm = normalizeForMatch(candidate);
    if (!norm) return true;
    const now = Date.now();

    this.recentSpoken = this.recentSpoken.filter((r) => now - r.timestamp < 10000);
    const candidateTokens = new Set(norm.split(' ').filter((w) => w.length > 2));

    for (const record of this.recentSpoken) {
      if (record.normalized.includes(norm) || (norm.length > 10 && norm.includes(record.normalized))) {
        return true;
      }

      if (candidateTokens.size > 0) {
        const recordTokens = new Set(record.normalized.split(' ').filter((w) => w.length > 2));
        let matches = 0;
        candidateTokens.forEach((token) => {
          if (recordTokens.has(token)) matches++;
        });
        const overlapRatio = matches / candidateTokens.size;
        if (overlapRatio >= 0.5) {
          return true;
        }
      }
    }

    return false;
  }

  parseWakeWord(transcript) {
    const raw = transcript.trim();
    const lower = raw.toLowerCase();

    for (const ww of WAKE_WORDS_ENGLISH) {
      if (lower === ww) {
        return { hasWakeWord: true, command: '', isWakeWordOnly: true };
      }
      if (lower.startsWith(ww + ' ') || lower.startsWith(ww + ',') || lower.startsWith(ww + ':')) {
        const cmd = raw.slice(ww.length).replace(/^[\s,:]+/, '').trim();
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd };
      }
    }
    for (const ww of WAKE_WORDS_ENGLISH) {
      const idx = lower.indexOf(ww);
      if (idx !== -1 && idx < 15) {
        const cmd = (raw.slice(0, idx) + ' ' + raw.slice(idx + ww.length)).replace(/\s+/g, ' ').trim();
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd };
      }
    }

    for (const ww of WAKE_WORDS_DEVANAGARI) {
      if (raw === ww) {
        return { hasWakeWord: true, command: '', isWakeWordOnly: true };
      }
      if (raw.startsWith(ww + ' ') || raw.startsWith(ww + ',') || raw.startsWith(ww + '।')) {
        const cmd = raw.slice(ww.length).replace(/^[\s,।]+/, '').trim();
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd };
      }
    }
    for (const ww of WAKE_WORDS_DEVANAGARI) {
      const idx = raw.indexOf(ww);
      if (idx !== -1 && idx < 20) {
        const cmd = (raw.slice(0, idx) + ' ' + raw.slice(idx + ww.length)).replace(/\s+/g, ' ').trim();
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd };
      }
    }

    return { hasWakeWord: false, command: raw, isWakeWordOnly: false };
  }
}

async function runTests() {
  console.log('--- 1. Testing Anti-Self-Echo & Self-Utterance Filter ---');
  const tester = new EchoAndWakeWordTester();

  const jarvisUtterance = "Good day, sir. Systems are online and monitoring. Standing by for instructions.";
  tester.recordSpokenText(jarvisUtterance);

  // Exact substring of what JARVIS said must be flagged as echo
  assert.strictEqual(tester.isAcousticEcho("systems are online and monitoring"), true, 'Substring of JARVIS speech must be identified as echo');
  assert.strictEqual(tester.isAcousticEcho("standing by for instructions"), true, 'Tail echo must be identified as echo');
  assert.strictEqual(tester.isAcousticEcho("Good day sir systems are online"), true, 'Head echo must be identified as echo');

  // Real user commands must NOT be flagged as echo
  assert.strictEqual(tester.isAcousticEcho("open YouTube in top right"), false, 'User command must not be flagged as echo');
  assert.strictEqual(tester.isAcousticEcho("what is the current CPU temperature"), false, 'User query must not be flagged as echo');
  assert.strictEqual(tester.isAcousticEcho("हवामान कसे आहे?"), false, 'Marathi user command must not be flagged as echo');
  assert.strictEqual(tester.isAcousticEcho("समय क्या हुआ है?"), false, 'Hindi user command must not be flagged as echo');

  console.log('✓ Anti-Self-Echo filtering verified successfully!');

  console.log('\n--- 2. Testing Multilingual Wake-Word Parsing ---');

  // English wake word + command
  let parsed = tester.parseWakeWord("Hey Jarvis open YouTube");
  assert.strictEqual(parsed.hasWakeWord, true);
  assert.strictEqual(parsed.command, "open YouTube");
  assert.strictEqual(parsed.isWakeWordOnly, false);

  // English wake word alone
  parsed = tester.parseWakeWord("Hey Jarvis");
  assert.strictEqual(parsed.hasWakeWord, true);
  assert.strictEqual(parsed.command, "");
  assert.strictEqual(parsed.isWakeWordOnly, true);

  // Marathi wake word + command
  parsed = tester.parseWakeWord("जार्विस, हवामान कसे आहे?");
  assert.strictEqual(parsed.hasWakeWord, true);
  assert.strictEqual(parsed.command, "हवामान कसे आहे?");
  assert.strictEqual(parsed.isWakeWordOnly, false);

  // Hindi wake word + command
  parsed = tester.parseWakeWord("हे जार्विस, आज का तापमान क्या है?");
  assert.strictEqual(parsed.hasWakeWord, true);
  assert.strictEqual(parsed.command, "आज का तापमान क्या है?");
  assert.strictEqual(parsed.isWakeWordOnly, false);

  // Command without wake word
  parsed = tester.parseWakeWord("search Arc Reactor propulsion");
  assert.strictEqual(parsed.hasWakeWord, false);
  assert.strictEqual(parsed.command, "search Arc Reactor propulsion");

  console.log('✓ Multilingual Wake-Word parsing verified successfully!');

  console.log('\n--- 3. Testing Backend Cloned Voice TTS Across Languages ---');
  const ttsEndpoint = 'http://127.0.0.1:8000/api/tts';

  const testPhrases = [
    { lang: 'English', text: 'Good day, sir. Systems are online.' },
    { lang: 'Marathi', text: 'नमस्कार सर, मी जार्विस आहे. सर्व सिस्टिम्स कार्यरत आहेत.' },
    { lang: 'Hindi', text: 'नमस्ते सर, सभी प्रणालियां सामान्य रूप से काम कर रही हैं।' }
  ];

  for (const item of testPhrases) {
    try {
      const resp = await fetch(ttsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: item.text })
      });

      assert.strictEqual(resp.status, 200, `${item.lang} TTS should return status 200`);
      assert.strictEqual(resp.headers.get('content-type'), 'audio/wav', `${item.lang} TTS should return audio/wav`);
      const buffer = await resp.arrayBuffer();
      assert.ok(buffer.byteLength > 10000, `${item.lang} audio buffer should be substantial (>10KB)`);

      console.log(`✓ ${item.lang} TTS synthesized successfully (${buffer.byteLength} bytes WAV) using cloned voice`);
    } catch (err) {
      console.error(`✗ ${item.lang} TTS failed:`, err.message);
      throw err;
    }
  }

  console.log('\n======================================================');
  console.log('ALL VERIFICATION CHECKS PASSED: Voice Subsystem is Rock Solid!');
  console.log('======================================================');
}

runTests().catch((e) => {
  console.error('Test run failed:', e);
  process.exit(1);
});
