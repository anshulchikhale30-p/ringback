/* PCM processor for the RingBack browser voice agent demo.
   Captures Float32 mic frames at 24 kHz and down-converts to Int16 PCM16,
   the wire format AssemblyAI's Voice Agent WebSocket expects. */
class RingBackPCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) {
      const buf = new Int16Array(ch.length);
      for (let i = 0; i < ch.length; i++) {
        buf[i] = ch[i] < 0 ? ch[i] * 0x8000 : ch[i] * 0x7fff;
      }
      this.port.postMessage(buf);
    }
    return true;
  }
}

registerProcessor("ringback-pcm", RingBackPCMProcessor);