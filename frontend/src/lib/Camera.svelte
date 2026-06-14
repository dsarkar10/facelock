<script>
  import { onMount } from "svelte";

  let video = $state(null);
  let canvas = $state(null);
  let stream = $state(null);
  let error = $state("");
  let faceDetected = $state(false);
  let fdSupported = $state(true);

  let { onCapture, compact = false } = $props();

  let detectTimer;

  onMount(() => {
    startCamera();
    return () => {
      clearInterval(detectTimer);
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  });

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (video) {
        video.srcObject = stream;
        video.onloadedmetadata = () => initDetector();
      }
    } catch {
      error = "Could not access camera";
    }
  }

  async function initDetector() {
    if (!window.FaceDetector) {
      fdSupported = false;
      return;
    }
    const detector = new FaceDetector({ maxDetectedFaces: 1 });
    detectTimer = setInterval(async () => {
      if (!video || video.readyState < 2) return;
      try {
        const faces = await detector.detect(video);
        faceDetected = faces.length > 0;
      } catch {
        faceDetected = false;
      }
    }, 500);
  }

  function capture() {
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob && onCapture) onCapture(blob);
    }, "image/jpeg");
  }
</script>

{#if error}
  <p class="error">{error}</p>
{/if}

<div class="camera-box" class:compact>
  <div class="video-wrap">
    <video bind:this={video} autoplay playsinline></video>
    {#if stream}
      <div
        class="oval"
        class:green={faceDetected}
        class:red={!faceDetected && fdSupported}
        class:neutral={!fdSupported}
      >
        <span class="oval-label">
          {#if !fdSupported}
            Position face in oval
          {:else if faceDetected}
            Face detected
          {:else}
            No face detected
          {/if}
        </span>
      </div>
    {/if}
  </div>
</div>

<canvas bind:this={canvas} style="display:none"></canvas>

<div class="actions">
  <button onclick={capture} disabled={!stream}>Capture</button>
</div>

<style>
  .camera-box {
    width: 100%;
  }
  .camera-box.compact {
    max-width: 300px;
    margin: 0 auto;
  }
  .camera-box.compact .oval-label {
    font-size: 0.6rem;
  }
  .video-wrap {
    position: relative;
    width: 100%;
    overflow: hidden;
    border-radius: 8px;
  }
  video {
    width: 100%;
    display: block;
    border-radius: 8px;
    background: #000;
  }
  .oval {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -55%);
    width: 50%;
    max-height: 90%;
    aspect-ratio: 3 / 4;
    border-radius: 50%;
    border: 3px solid;
    pointer-events: none;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color 0.25s, background-color 0.25s;
  }
  .oval.red {
    border-color: #ef4444;
    background: rgba(239, 68, 68, 0.07);
  }
  .oval.green {
    border-color: #22c55e;
    background: rgba(34, 197, 94, 0.07);
  }
  .oval.neutral {
    border-color: #6366f1;
    background: rgba(99, 102, 241, 0.07);
  }
  .oval-label {
    font-size: 0.7rem;
    color: #fff;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.7);
    background: rgba(0, 0, 0, 0.45);
    padding: 2px 10px;
    border-radius: 4px;
    white-space: nowrap;
  }
  .actions {
    display: flex;
    justify-content: center;
    margin-top: 0.75rem;
  }
  button {
    padding: 0.6rem 2rem;
    font-size: 1rem;
    border: none;
    border-radius: 6px;
    background: #4f46e5;
    color: #fff;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .error {
    color: #dc2626;
    margin-bottom: 0.5rem;
    text-align: center;
  }
</style>
