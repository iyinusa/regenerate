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
  const frameIdRef = useRef<number>(0);
  const themeRef = useRef<'day' | 'night'>('night');

  // Determine initial theme based on time
  const [theme] = useState<'day' | 'night'>(() => {
    const hour = new Date().getHours();
    return (hour >= 6 && hour < 18) ? 'day' : 'night';
  });

  useEffect(() => {
    if (!containerRef.current) return;
    
    // Update ref for animation loop access
    themeRef.current = theme;

    // Scene setup
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Fog for depth - adapts to theme
    const fogColor = theme === 'day' ? 0xf0f5ff : 0x050510;
    scene.fog = new THREE.FogExp2(fogColor, 0.02);

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.z = 30;
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true 
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    
    // Clear color matches fog
    renderer.setClearColor(fogColor, 1); 
    
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Create particle system
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 5000;
    const posArray = new Float32Array(particlesCount * 3);
    const colorArray = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i += 3) {
      posArray[i] = (Math.random() - 0.5) * 100;
      posArray[i + 1] = (Math.random() - 0.5) * 100;
      posArray[i + 2] = (Math.random() - 0.5) * 100;

      // Color gradient
      // Day: Blue/Teal/Gold cues
      // Night: Cyan/Purple/Pink cues
      const t = Math.random();
      if (theme === 'day') {
         // Silvery/Blue for day
         colorArray[i] = 0.1 + t * 0.2; // R
         colorArray[i + 1] = 0.3 + t * 0.4; // G
         colorArray[i + 2] = 0.8 + t * 0.2; // B
      } else {
         // Neon for night
         colorArray[i] = 0.0 + t * 0.48; // R
         colorArray[i + 1] = 0.83 - t * 0.64; // G
         colorArray[i + 2] = 1.0 - t * 0.03; // B
      }
    }

    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));

    const particlesMaterial = new THREE.PointsMaterial({
      size: theme === 'day' ? 0.2 : 0.15, // Slightly larger particles in day to be visible
      vertexColors: true,
      transparent: true,
      opacity: theme === 'day' ? 0.9 : 0.8,
      // Use NormalBlending for Day so they show up against light bg, Additive for Night
      blending: theme === 'day' ? THREE.NormalBlending : THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particles);
    particlesRef.current = particles;

    // Add ambient light
    const ambientLight = new THREE.AmbientLight(
      theme === 'day' ? 0xffffff : 0x404040, 
      theme === 'day' ? 1.5 : 2
    );
    scene.add(ambientLight);

    // Add directional light (Sun/Moon)
    const directionalLight = new THREE.DirectionalLight(
      theme === 'day' ? 0xffaa00 : 0x00d4ff, 
      1
    );
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);

    // Add point lights for dynamic glow
    const pointLight1 = new THREE.PointLight(
      theme === 'day' ? 0x0088ff : 0x00d4ff, 
      2, 
      50
    );
    pointLight1.position.set(10, 10, 10);
    scene.add(pointLight1);

    const pointLight2 = new THREE.PointLight(
      theme === 'day' ? 0xff8800 : 0x7b2ff7, 
      2, 
      50
    );
    pointLight2.position.set(-10, -10, -10);
    scene.add(pointLight2);

    // Create floating geometric shapes
    const geometries = [
      new THREE.TetrahedronGeometry(2, 0),
      new THREE.OctahedronGeometry(1.5, 0),
      new THREE.IcosahedronGeometry(1.8, 0),
    ];

    const shapeMaterial = new THREE.MeshPhongMaterial({
      color: theme === 'day' ? 0x224488 : 0x00d4ff,
      transparent: true,
      opacity: 0.3,
      wireframe: true,
    });

    const shapes: THREE.Mesh[] = [];
    geometries.forEach((geometry) => {
      const mesh = new THREE.Mesh(geometry, shapeMaterial);
      mesh.position.set(
        (Math.random() - 0.5) * 40,
        (Math.random() - 0.5) * 40,
        (Math.random() - 0.5) * 40
      );
      scene.add(mesh);
      shapes.push(mesh);
    });

    // Mouse movement for parallax
    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      mouseX = (event.clientX / window.innerWidth) * 2 - 1;
      mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Handle window resize
    const handleResize = () => {
      if (!cameraRef.current || !rendererRef.current) return;
      
      cameraRef.current.aspect = window.innerWidth / window.innerHeight;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    // Animation loop
    let time = 0;
    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate);
      time += 0.001;

      if (particlesRef.current) {
        particlesRef.current.rotation.y = time * 0.5;
        particlesRef.current.rotation.x = time * 0.3;
      }

      // Animate geometric shapes
      shapes.forEach((shape, i) => {
        shape.rotation.x += 0.005 * (i + 1);
        shape.rotation.y += 0.003 * (i + 1);
        shape.position.y = Math.sin(time * 2 + i) * 2;
      });

      // Camera parallax based on mouse
      if (cameraRef.current) {
        gsap.to(cameraRef.current.position, {
          x: mouseX * 2,
          y: mouseY * 2,
          duration: 1,
          ease: 'power2.out',
        });
        cameraRef.current.lookAt(scene.position);
      }

      // Animate point lights
      pointLight1.position.x = Math.sin(time * 2) * 10;
      pointLight1.position.z = Math.cos(time * 2) * 10;
      pointLight2.position.x = Math.cos(time * 1.5) * 10;
      pointLight2.position.z = Math.sin(time * 1.5) * 10;

      if (rendererRef.current && cameraRef.current) {
        rendererRef.current.render(scene, cameraRef.current);
      }
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(frameIdRef.current);
      
      if (containerRef.current && rendererRef.current) {
        containerRef.current.removeChild(rendererRef.current.domElement);
      }
      
      particlesGeometry.dispose();
      particlesMaterial.dispose();
      geometries.forEach(g => g.dispose());
      shapeMaterial.dispose();
      rendererRef.current?.dispose();
    };
  }, [theme]);

  // Update scene based on active section
  useEffect(() => {
    if (!particlesRef.current) return;

    const colors = [
      [0.0, 0.83, 1.0], // Cyan
      [0.48, 0.19, 0.97], // Purple
      [1.0, 0.18, 0.59], // Pink
      [0.0, 0.83, 1.0], // Cyan
      [0.48, 0.19, 0.97], // Purple
      [1.0, 0.18, 0.59], // Pink
    ];

    const targetColor = colors[activeSection] || colors[0];
    
    gsap.to(sceneRef.current?.fog || {}, {
      duration: 1.5,
      ease: 'power2.inOut',
    });

    // Animate particle colors
    const colorAttribute = particlesRef.current.geometry.getAttribute('color');
    const colorArray = colorAttribute.array as Float32Array;
    
    for (let i = 0; i < colorArray.length; i += 3) {
      const t = (i / colorArray.length) + Math.random() * 0.2;
      gsap.to(colorArray, {
        [i]: targetColor[0] + t * 0.2,
        [i + 1]: targetColor[1] - t * 0.2,
        [i + 2]: targetColor[2],
        duration: 2,
        ease: 'power2.inOut',
        onUpdate: () => {
          colorAttribute.needsUpdate = true;
        },
      });
    }
  }, [activeSection]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 1,
        pointerEvents: 'none',
        backgroundColor: theme === 'day' ? '#f0f5ff' : '#050510',
        transition: 'background-color 2s ease-in-out',
      }}
    />
  );
};

export default JourneyBackground;
