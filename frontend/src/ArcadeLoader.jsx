import { useRef, useEffect, useState, useCallback } from "react";

/**
 * ArcadeLoader
 * -------------
 * Old-school vector arcade game als Ladeanzeige.
 * Erscheint EINGEBETTET im Layout (kein Fullscreen-Overlay), sobald die KI
 * zu rechnen beginnt (active=true), und verschwindet von selbst, sobald sie
 * fertig ist (active=false). So bleibt der restliche Screen sichtbar und es
 * entsteht kein Gefühl von Kontrollverlust.
 *
 * Steuerung: Pfeiltasten / A-D (nur wenn das Spielfeld fokussiert ist) /
 * Touch + Maus (Finger/Cursor ziehen). Ziel: den Asteroiden ausweichen.
 *
 * Keine externen Abhängigkeiten, keine Netzwerkaufrufe, kein localStorage.
 * Reines Canvas + requestAnimationFrame.
 *
 * Props:
 *   active   {boolean}  Spiel anzeigen (true während KI rechnet).
 *   message  {string}   Optionaler Text unter dem Spielfeld.
 *   width    {number}   Breite des eingebetteten Spielfelds in px (Default 380).
 *   height   {number}   Höhe des eingebetteten Spielfelds in px (Default 500).
 *   onExit   {function} Optionaler Callback nach dem Ausblenden.
 */
export default function ArcadeLoader({
  active = true,
  message = "Die KI denkt nach …",
  width = 380,
  height = 500,
  onExit,
}) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const stateRef = useRef(null);
  const rafRef = useRef(0);
  const [visible, setVisible] = useState(active);
  const [fading, setFading] = useState(false);
  const [score, setScore] = useState(0);

  // --- Ein-/Ausblenden anhand des active-Props -----------------------------
  useEffect(() => {
    if (active) {
      setVisible(true);
      setFading(false);
    } else if (visible) {
      setFading(true);
      const t = setTimeout(() => {
        setVisible(false);
        onExit && onExit();
      }, 600); // muss zur CSS-Transition unten passen
      return () => clearTimeout(t);
    }
  }, [active, visible, onExit]);

  // --- Game-Loop ------------------------------------------------------------
  const loop = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    const s = stateRef.current;
    if (!s) return;

    const now = performance.now();
    const dt = Math.min(48, now - s.last) / 16.6667; // in "Frames" (~60fps)
    s.last = now;

    // Schwierigkeit steigt langsam mit der Zeit
    s.elapsed += dt;
    const speed = 2.4 + s.elapsed * 0.0009;
    const spawnEvery = Math.max(22, 46 - s.elapsed * 0.012);

    // --- Eingabe -> Schiffsbewegung
    const accel = 0.55;
    const maxV = 7.5;
    if (s.left) s.vx -= accel * dt;
    if (s.right) s.vx += accel * dt;
    if (s.target != null) {
      // Touch-Ziel: weich anfahren
      s.vx += Math.sign(s.target - s.ship.x) *
        Math.min(maxV, Math.abs(s.target - s.ship.x) * 0.08) * 0.4 * dt;
    }
    if (!s.left && !s.right && s.target == null) s.vx *= Math.pow(0.86, dt);
    s.vx = Math.max(-maxV, Math.min(maxV, s.vx));
    s.ship.x += s.vx * dt;
    const margin = 18;
    if (s.ship.x < margin) { s.ship.x = margin; s.vx = 0; }
    if (s.ship.x > W - margin) { s.ship.x = W - margin; s.vx = 0; }

    // --- Sternenfeld (Hintergrund, scrollt nach unten)
    for (const star of s.stars) {
      star.y += (star.z * 0.6 + 0.3) * speed * dt;
      if (star.y > H) { star.y = 0; star.x = Math.random() * W; }
    }

    // --- Asteroiden spawnen
    s.spawnT += dt;
    if (s.spawnT >= spawnEvery) {
      s.spawnT = 0;
      const r = 10 + Math.random() * 26;
      s.rocks.push({
        x: r + Math.random() * (W - 2 * r),
        y: -r,
        r,
        vx: (Math.random() - 0.5) * 1.2,
        rot: Math.random() * Math.PI,
        vrot: (Math.random() - 0.5) * 0.06,
        verts: makeRockVerts(r),
        hit: false,
      });
    }

    // --- Asteroiden bewegen + Kollision
    const ship = s.ship;
    for (const rock of s.rocks) {
      rock.y += speed * dt;
      rock.x += rock.vx * dt;
      rock.rot += rock.vrot * dt;
      if (rock.x < rock.r || rock.x > W - rock.r) rock.vx *= -1;

      if (!rock.hit && !s.invuln) {
        const dx = rock.x - ship.x;
        const dy = rock.y - ship.y;
        if (Math.hypot(dx, dy) < rock.r + 12) {
          rock.hit = true;
          s.invuln = 70; // ~1,1 s Unverwundbarkeit + Blinken
          s.lives -= 1;
          s.shake = 14;
          if (s.lives < 0) {
            // sanfter Neustart statt Game Over – es ist ein Ladescreen
            s.lives = 2;
            s.score = Math.max(0, s.score - 200);
          }
        }
      }
    }
    // gepasste Felsen zählen
    s.rocks = s.rocks.filter((r) => {
      if (r.y - r.r > H) {
        if (!r.hit) s.score += 10;
        return false;
      }
      return true;
    });

    if (s.invuln > 0) s.invuln -= dt;
    if (s.shake > 0) s.shake -= dt;
    s.score += 0.12 * dt; // Überlebens-Bonus

    // Score nur gelegentlich an React melden (Performance)
    s.scoreSync += dt;
    if (s.scoreSync > 6) { s.scoreSync = 0; setScore(Math.floor(s.score)); }

    // --- Zeichnen -----------------------------------------------------------
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, W, H);

    const shake = s.shake > 0 ? (Math.random() - 0.5) * s.shake : 0;
    ctx.save();
    ctx.translate(shake, shake * 0.5);

    // Sterne
    for (const star of s.stars) {
      const a = 0.25 + star.z * 0.55;
      ctx.fillStyle = `rgba(255,255,255,${a})`;
      const sz = star.z > 0.7 ? 2 : 1;
      ctx.fillRect(star.x, star.y, sz, sz);
    }

    // Asteroiden (Vektor-Outline)
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = "#fff";
    for (const rock of s.rocks) {
      ctx.save();
      ctx.translate(rock.x, rock.y);
      ctx.rotate(rock.rot);
      ctx.beginPath();
      rock.verts.forEach((v, i) => {
        const px = Math.cos(v.a) * v.r;
        const py = Math.sin(v.a) * v.r;
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.stroke();
      ctx.restore();
    }

    // Schiff (Vektor-Dreieck), blinkt bei Unverwundbarkeit
    const blink = s.invuln > 0 && Math.floor(s.invuln / 5) % 2 === 0;
    if (!blink) {
      ctx.save();
      ctx.translate(ship.x, ship.y);
      const tilt = s.vx * 0.04;
      ctx.rotate(tilt);
      ctx.strokeStyle = "#4ade80";
      ctx.fillStyle = "rgba(74,222,128,0.12)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, -16);
      ctx.lineTo(11, 12);
      ctx.lineTo(0, 6);
      ctx.lineTo(-11, 12);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      // Triebwerk-Flamme
      ctx.strokeStyle = "rgba(250,204,21,0.9)";
      ctx.beginPath();
      ctx.moveTo(-4, 8);
      ctx.lineTo(0, 14 + Math.random() * 6);
      ctx.lineTo(4, 8);
      ctx.stroke();
      ctx.restore();
    }

    ctx.restore();

    // HUD
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = "14px ui-monospace, Menlo, Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText(`SCORE ${String(Math.floor(s.score)).padStart(5, "0")}`, 14, 24);
    ctx.textAlign = "right";
    ctx.fillText("♥".repeat(Math.max(0, s.lives + 1)), W - 14, 24);

    rafRef.current = requestAnimationFrame(loop);
  }, []);

  // --- Setup / Teardown -----------------------------------------------------
  useEffect(() => {
    if (!visible) return;
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;

    function resize() {
      const w = wrap.clientWidth;
      const h = wrap.clientHeight;
      // Wir rechnen die Spielwelt direkt in CSS-Pixeln (einfach & robust).
      canvas.width = w;
      canvas.height = h;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      if (stateRef.current) {
        stateRef.current.ship.x = Math.min(stateRef.current.ship.x, w - 18);
        stateRef.current.ship.y = h - 46;
      }
    }

    // State initialisieren
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    const stars = Array.from({ length: 90 }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      z: Math.random(),
    }));
    stateRef.current = {
      ship: { x: w / 2, y: h - 46 },
      vx: 0,
      left: false,
      right: false,
      target: null,
      rocks: [],
      stars,
      spawnT: 0,
      elapsed: 0,
      score: 0,
      scoreSync: 0,
      lives: 2,
      invuln: 0,
      shake: 0,
      last: performance.now(),
    };

    resize();
    window.addEventListener("resize", resize);

    // Tastatur
    const down = (e) => {
      const s = stateRef.current;
      if (!s) return;
      if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") { s.left = true; e.preventDefault(); }
      if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") { s.right = true; e.preventDefault(); }
    };
    const up = (e) => {
      const s = stateRef.current;
      if (!s) return;
      if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") s.left = false;
      if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") s.right = false;
    };
    // Tastatur nur am Spielfeld lauschen (nicht global), damit Pfeiltasten
    // nicht die ganze Seite scrollen – kein Kontrollverlust für den Nutzer.
    wrap.addEventListener("keydown", down);
    wrap.addEventListener("keyup", up);

    // Touch / Maus: Finger-Position = Ziel
    const setTarget = (clientX) => {
      const s = stateRef.current;
      const rect = canvas.getBoundingClientRect();
      if (s) s.target = clientX - rect.left;
    };
    const onTouchMove = (e) => { setTarget(e.touches[0].clientX); e.preventDefault(); };
    const onTouchStart = (e) => { wrap.focus({ preventScroll: true }); setTarget(e.touches[0].clientX); };
    const onTouchEnd = () => { if (stateRef.current) stateRef.current.target = null; };
    const onMouseMove = (e) => setTarget(e.clientX);
    const onMouseDown = () => wrap.focus({ preventScroll: true });
    canvas.addEventListener("touchstart", onTouchStart, { passive: true });
    canvas.addEventListener("touchmove", onTouchMove, { passive: false });
    canvas.addEventListener("touchend", onTouchEnd);
    canvas.addEventListener("mousemove", onMouseMove);
    wrap.addEventListener("mousedown", onMouseDown);

    // Beim Erscheinen Fokus holen (ohne Seitensprung), damit Tasten sofort gehen.
    wrap.focus({ preventScroll: true });

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
      wrap.removeEventListener("keydown", down);
      wrap.removeEventListener("keyup", up);
      canvas.removeEventListener("touchstart", onTouchStart);
      canvas.removeEventListener("touchmove", onTouchMove);
      canvas.removeEventListener("touchend", onTouchEnd);
      canvas.removeEventListener("mousemove", onMouseMove);
      wrap.removeEventListener("mousedown", onMouseDown);
    };
  }, [visible, loop]);

  if (!visible) return null;

  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        maxWidth: "100%",
        opacity: fading ? 0 : 1,
        transition: "opacity 0.6s ease",
        userSelect: "none",
      }}
    >
      <div
        ref={wrapRef}
        tabIndex={0}
        aria-label="Arcade-Spiel zum Überbrücken der Wartezeit"
        style={{
          position: "relative",
          width: width,
          height: height,
          maxWidth: "100%",
          background: "#000",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 12,
          overflow: "hidden",
          outline: "none",
          touchAction: "none",
          boxShadow: "0 0 40px rgba(74,222,128,0.06)",
        }}
      >
        <canvas ref={canvasRef} style={{ display: "block", width: "100%", height: "100%" }} />
      </div>
      <p
        style={{
          marginTop: 18,
          color: "rgba(255,255,255,0.6)",
          font: "14px ui-monospace, Menlo, Consolas, monospace",
          letterSpacing: 0.5,
          textAlign: "center",
        }}
      >
        {message}
        <br />
        <span style={{ fontSize: 12, opacity: 0.55 }}>
          {"← → / A · D oder Finger ziehen · Score "}{score}
        </span>
      </p>
    </div>
  );
}

// Unregelmäßige Asteroiden-Form als Liste von Eckpunkten
function makeRockVerts(r) {
  const n = 8 + Math.floor(Math.random() * 4);
  return Array.from({ length: n }, (_, i) => ({
    a: (i / n) * Math.PI * 2,
    r: r * (0.72 + Math.random() * 0.4),
  }));
}
