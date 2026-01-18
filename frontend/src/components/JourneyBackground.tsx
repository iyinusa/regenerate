import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { gsap } from 'gsap';

interface JourneyBackgroundProps {
  activeSection?: number;
}

const JourneyBackground: React.FC<JourneyBackgroundProps> = ({ activeSection = 0 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const particlesRef = useRef<THREE.Points | null>(null);
  const atmosphericParticlesRef = useRef<THREE.Points | null>(null);
  const shapesRef = useRef<THREE.Mesh[]>([]);
  const frameIdRef = useRef<number>(0);
  const mouseXRef = useRef(0);
  const mouseYRef = useRef(0);

  // Determine initial theme based on time
  const [theme] = useState<'day' | 'night'>(() => {
    const hour = new Date().getHours();
    return (hour >= 6 && hour < 18) ? 'day' : 'night';
  });

  // Section color configurations
  const sectionColors = [
    { primary: 0x00d4ff, secondary: 0x0099cc }, // Hero - Cyan
    { primary: 0x7b2ff7, secondary: 0x5a1fd6 }, // Timeline - Purple
    { primary: 0xff2e97, secondary: 0xcc2579 }, // Experience - Pink
    { primary: 0x00ff88, secondary: 0x00cc6a }, // Skills - Green
    { primary: 0xffaa00, secondary: 0xcc8800 }, // Projects - Orange
    { primary: 0xff4444, secondary: 0xcc3636 }, // Documentary - Red
  ];

  useEffect(() => {
    if (!containerRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Helper to create circular space particle texture
    const createParticleTexture = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 32;
      canvas.height = 32;
      const context = canvas.getContext('2d');
      if (!context) return null;

      const gradient = context.createRadialGradient(16, 16, 0, 16, 16, 16);
      gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
      gradient.addColorStop(0.2, 'rgba(255, 255, 255, 0.8)');
      gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.2)');
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

      context.clearRect(0, 0, 32, 32);
      context.fillStyle = gradient;
      context.fillRect(0, 0, 32, 32);

      const texture = new THREE.CanvasTexture(canvas);
      return texture;
    };

    const particleTexture = createParticleTexture();

    const bgColor = theme === 'day' ? 0x2b4c7e : 0x030308;
    scene.fog = new THREE.FogExp2(bgColor, 0.008);

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      0.1,
      2000
    );
    camera.position.set(0, 0, 100);
    cameraRef.current = camera;

    // Renderer setup - simple and proven approach
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(bgColor, 1);
    
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Create main particle system
    const createParticles = () => {
      const geometry = new THREE.BufferGeometry();
      const count = 3000;
      const positions = new Float32Array(count * 3);
      const colors = new Float32Array(count * 3);

      for (let i = 0; i < count; i++) {
        const i3 = i * 3;
        
        // Spherical distribution
        const radius = 50 + Math.random() * 150;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        
        positions[i3] = radius * Math.sin(phi) * Math.cos(theta);
        positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
        positions[i3 + 2] = radius * Math.cos(phi);

        // Color based on section
        const colorConfig = sectionColors[activeSection] || sectionColors[0];
        const color = new THREE.Color(Math.random() > 0.5 ? colorConfig.primary : colorConfig.secondary);
        const intensity = 0.5 + Math.random() * 0.5;
        
        colors[i3] = color.r * intensity;
        colors[i3 + 1] = color.g * intensity;
        colors[i3 + 2] = color.b * intensity;
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const material = new THREE.PointsMaterial({
        size: 1.5,
        map: particleTexture,
        depthWrite: false,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending,
        sizeAttenuation: true
      });

      const particles = new THREE.Points(geometry, material);
      scene.add(particles);
      particlesRef.current = particles;
    };

    // Create atmospheric dust particles
    const createAtmosphericParticles = () => {
      const geometry = new THREE.BufferGeometry();
      const count = 500;
      const positions = new Float32Array(count * 3);
      const colors = new Float32Array(count * 3);

      for (let i = 0; i < count; i++) {
        const i3 = i * 3;
        positions[i3] = (Math.random() - 0.5) * 400;
        positions[i3 + 1] = (Math.random() - 0.5) * 400;
        positions[i3 + 2] = (Math.random() - 0.5) * 200;

        const intensity = 0.2 + Math.random() * 0.3;
        colors[i3] = intensity;
        colors[i3 + 1] = intensity;
        colors[i3 + 2] = intensity;
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const material = new THREE.PointsMaterial({
        size: 2.5,
        map: particleTexture,
        depthWrite: false,
        vertexColors: true,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending
      });

      const particles = new THREE.Points(geometry, material);
      scene.add(particles);
      atmosphericParticlesRef.current = particles;
    };

    // Create floating geometric shapes
    const createShapes = () => {
      const geometries = [
        new THREE.TetrahedronGeometry(3, 0),
        new THREE.OctahedronGeometry(2.5, 0),
        new THREE.IcosahedronGeometry(2.8, 0),
        new THREE.DodecahedronGeometry(2.2, 0),
      ];

      geometries.forEach((geometry, index) => {
        const colorConfig = sectionColors[activeSection] || sectionColors[0];
        const material = new THREE.MeshBasicMaterial({
          color: index % 2 === 0 ? colorConfig.primary : colorConfig.secondary,
          wireframe: true,
          transparent: true,
          opacity: 0.4
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(
          (Math.random() - 0.5) * 80,
          (Math.random() - 0.5) * 80,
          (Math.random() - 0.5) * 40
        );
        mesh.rotation.set(
          Math.random() * Math.PI,
          Math.random() * Math.PI,
          Math.random() * Math.PI
        );

        scene.add(mesh);
        shapesRef.current.push(mesh);

        // Animate rotation
        gsap.to(mesh.rotation, {
          x: mesh.rotation.x + Math.PI * 2,
          y: mesh.rotation.y + Math.PI * 2,
          duration: 15 + Math.random() * 10,
          repeat: -1,
          ease: 'none'
        });
      });
    };

    // Add lights
    const addLights = () => {
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
      scene.add(ambientLight);

      const colorConfig = sectionColors[activeSection] || sectionColors[0];
      
      const pointLight1 = new THREE.PointLight(colorConfig.primary, 2, 200);
      pointLight1.position.set(50, 50, 50);
      scene.add(pointLight1);

      const pointLight2 = new THREE.PointLight(colorConfig.secondary, 1.5, 200);
      pointLight2.position.set(-50, -50, 50);
      scene.add(pointLight2);
    };

    createParticles();
    createAtmosphericParticles();
    createShapes();
    addLights();

    // Mouse movement handler
    const handleMouseMove = (event: MouseEvent) => {
      mouseXRef.current = (event.clientX / window.innerWidth) * 2 - 1;
      mouseYRef.current = -(event.clientY / window.innerHeight) * 2 + 1;
    };

    // Resize handler
    const handleResize = () => {
      if (!camera || !renderer) return;
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('resize', handleResize);

    // Animation loop
    let time = 0;
    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate);
      time += 0.01;

      // Rotate main particles
      if (particlesRef.current) {
        particlesRef.current.rotation.y += 0.001;
        particlesRef.current.rotation.x += 0.0005;
        
        // Pulsing opacity
        const material = particlesRef.current.material as THREE.PointsMaterial;
        material.opacity = 0.6 + Math.sin(time * 2) * 0.2;
      }

      // Animate atmospheric particles
      if (atmosphericParticlesRef.current) {
        atmosphericParticlesRef.current.rotation.y -= 0.0003;
        atmosphericParticlesRef.current.position.x = Math.sin(time * 0.5) * 5;
      }

      // Animate shapes
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const scrollFraction = maxScroll > 0 ? window.scrollY / maxScroll : 0;
      const targetScale = 1 + scrollFraction * 2.0;

      shapesRef.current.forEach((shape, i) => {
        shape.position.y += Math.sin(time + i) * 0.02;
        const material = shape.material as THREE.MeshBasicMaterial;
        material.opacity = 0.3 + Math.sin(time * 2 + i) * 0.15;
        
        // Scale effect based on scroll
        shape.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.05);
      });

      // Camera parallax
      if (camera) {
        camera.position.x += (mouseXRef.current * 10 - camera.position.x) * 0.02;
        camera.position.y += (mouseYRef.current * 10 - camera.position.y) * 0.02;
        camera.lookAt(scene.position);
      }

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(frameIdRef.current);
      
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement);
      }
      
      renderer.dispose();
      particleTexture?.dispose();
      
      // Dispose geometries and materials
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry?.dispose();
          if (child.material) {
            if (Array.isArray(child.material)) {
              child.material.forEach(m => m.dispose());
            } else {
              child.material.dispose();
            }
          }
        }
        if (child instanceof THREE.Points) {
          child.geometry?.dispose();
          (child.material as THREE.Material)?.dispose();
        }
      });
    };
  }, [theme]);

  // Update colors when section changes
  useEffect(() => {
    if (!particlesRef.current || !sceneRef.current) return;

    const colorConfig = sectionColors[activeSection] || sectionColors[0];
    const primaryColor = new THREE.Color(colorConfig.primary);
    const secondaryColor = new THREE.Color(colorConfig.secondary);

    // Update particle colors
    const colors = particlesRef.current.geometry.getAttribute('color');
    const colorArray = colors.array as Float32Array;
    
    for (let i = 0; i < colorArray.length; i += 3) {
      const color = Math.random() > 0.5 ? primaryColor : secondaryColor;
      const intensity = 0.5 + Math.random() * 0.5;
      
      gsap.to(colorArray, {
        [i]: color.r * intensity,
        [i + 1]: color.g * intensity,
        [i + 2]: color.b * intensity,
        duration: 2,
        ease: 'power2.inOut',
        onUpdate: () => {
          colors.needsUpdate = true;
        }
      });
    }

    // Update shape colors
    shapesRef.current.forEach((shape, index) => {
      const material = shape.material as THREE.MeshBasicMaterial;
      const targetColor = index % 2 === 0 ? colorConfig.primary : colorConfig.secondary;
      gsap.to(material.color, {
        r: new THREE.Color(targetColor).r,
        g: new THREE.Color(targetColor).g,
        b: new THREE.Color(targetColor).b,
        duration: 1.5,
        ease: 'power2.inOut'
      });
    });
  }, [activeSection]);

  return (
    <div
      ref={containerRef}
      className="three-container journey-bg"
    />
  );
};

export default JourneyBackground;
