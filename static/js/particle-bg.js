// static/js/particle-bg.js
class ParticleBackground {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.particles = [];
    this.animationId = null;
    this.mouseX = null;
    this.mouseY = null;
    this.isLightTheme = false;
  }

  init(containerId = "particle-container") {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Clear container
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    // Create canvas
    this.canvas = document.createElement("canvas");
    this.canvas.style.position = "absolute";
    this.canvas.style.top = "0";
    this.canvas.style.left = "0";
    this.canvas.style.width = "100%";
    this.canvas.style.height = "100%";
    this.canvas.style.display = "block";
    container.appendChild(this.canvas);

    this.ctx = this.canvas.getContext("2d");

    // Set initial theme
    this.isLightTheme = document.body.classList.contains("light-theme");

    // Handle resize
    window.addEventListener("resize", () => this.resize());
    this.resize();

    // Mouse move for interaction
    window.addEventListener("mousemove", (e) => {
      this.mouseX = e.clientX;
      this.mouseY = e.clientY;
    });

    window.addEventListener("mouseleave", () => {
      this.mouseX = null;
      this.mouseY = null;
    });

    // Create particles
    this.createParticles();

    // Start animation
    this.animate();

    // Watch for theme changes
    this.observeThemeChanges();
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    this.createParticles(); // Recreate particles on resize
  }

  createParticles() {
    const particleCount = Math.min(
      150,
      Math.floor((window.innerWidth * window.innerHeight) / 15000),
    );
    this.particles = [];

    for (let i = 0; i < particleCount; i++) {
      this.particles.push({
        x: Math.random() * this.canvas.width,
        y: Math.random() * this.canvas.height,
        radius: Math.random() * 3 + 1.5,
        alpha: Math.random() * 0.4 + 0.2,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        originalX: Math.random() * this.canvas.width,
        originalY: Math.random() * this.canvas.height,
      });
    }
  }

  getParticleColor() {
    if (this.isLightTheme) {
      // Dark particles for light theme
      return `rgba(0, 0, 0, `;
    } else {
      // Light particles for dark theme
      return `rgba(255, 255, 255, `;
    }
  }

  drawParticles() {
    if (!this.ctx) return;

    // Clear canvas with transparency
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw connecting lines first (behind particles)
    this.ctx.beginPath();
    for (let i = 0; i < this.particles.length; i++) {
      for (let j = i + 1; j < this.particles.length; j++) {
        const dx = this.particles[i].x - this.particles[j].x;
        const dy = this.particles[i].y - this.particles[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < 120) {
          const opacity = (1 - distance / 120) * 0.15;
          if (this.isLightTheme) {
            this.ctx.strokeStyle = `rgba(0, 0, 0, ${opacity})`;
          } else {
            this.ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
          }
          this.ctx.lineWidth = 0.8;
          this.ctx.beginPath();
          this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
          this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
          this.ctx.stroke();
        }
      }
    }

    // Draw particles
    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      const gradient = this.ctx.createRadialGradient(
        p.x,
        p.y,
        0,
        p.x,
        p.y,
        p.radius,
      );

      if (this.isLightTheme) {
        gradient.addColorStop(0, `rgba(0, 0, 0, ${p.alpha * 0.9})`);
        gradient.addColorStop(1, `rgba(0, 0, 0, ${p.alpha * 0.3})`);
      } else {
        gradient.addColorStop(0, `rgba(255, 255, 255, ${p.alpha * 0.9})`);
        gradient.addColorStop(1, `rgba(255, 255, 255, ${p.alpha * 0.2})`);
      }

      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = gradient;
      this.ctx.fill();
    }
  }

  updateParticles() {
    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      // Mouse repulsion
      if (this.mouseX && this.mouseY) {
        const dx = p.x - this.mouseX;
        const dy = p.y - this.mouseY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const minDistance = 100;

        if (distance < minDistance) {
          const angle = Math.atan2(dy, dx);
          const force = ((minDistance - distance) / minDistance) * 2;
          p.x += Math.cos(angle) * force;
          p.y += Math.sin(angle) * force;
        }
      }

      // Move particles
      p.x += p.vx;
      p.y += p.vy;

      // Return to original position slowly
      p.x += (p.originalX - p.x) * 0.01;
      p.y += (p.originalY - p.y) * 0.01;

      // Wrap around edges with slight randomness
      if (p.x < -50) p.x = this.canvas.width + 50;
      if (p.x > this.canvas.width + 50) p.x = -50;
      if (p.y < -50) p.y = this.canvas.height + 50;
      if (p.y > this.canvas.height + 50) p.y = -50;

      // Occasional direction change
      if (Math.random() < 0.005) {
        p.vx += (Math.random() - 0.5) * 0.2;
        p.vy += (Math.random() - 0.5) * 0.2;
        // Limit velocity
        p.vx = Math.min(Math.max(p.vx, -0.8), 0.8);
        p.vy = Math.min(Math.max(p.vy, -0.8), 0.8);
      }
    }
  }

  updateTheme() {
    this.isLightTheme = document.body.classList.contains("light-theme");
    // Particles will update colors on next draw
  }

  observeThemeChanges() {
    const observer = new MutationObserver(() => {
      this.updateTheme();
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["class"],
    });
  }

  animate() {
    this.updateParticles();
    this.drawParticles();
    this.animationId = requestAnimationFrame(() => this.animate());
  }

  destroy() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
  }
}

// Initialize
const particleBg = new ParticleBackground();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    particleBg.init();
  });
} else {
  particleBg.init();
}

export default particleBg;
