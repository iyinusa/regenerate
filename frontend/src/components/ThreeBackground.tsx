import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { gsap } from 'gsap';

const ThreeBackground: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const particlesRef = useRef<THREE.Points | null>(null);
  const geometriesRef = useRef<THREE.Mesh[]>([]);
  const mouseXRef = useRef(0);
  const mouseYRef = useRef(0);
  const windowHalfXRef = useRef(0);
  const windowHalfYRef = useRef(0);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize
    init();
    animate();

    const handleResize = () => {
      if (!cameraRef.current || !rendererRef.current) return;
      windowHalfXRef.current = window.innerWidth / 2;
      windowHalfYRef.current = window.innerHeight / 2;
      cameraRef.current.aspect = window.innerWidth / window.innerHeight;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(window.innerWidth, window.innerHeight);
    };

    const handleMouseMove = (event: MouseEvent) => {
      mouseXRef.current = (event.clientX - windowHalfXRef.current) * 0.1;
      mouseYRef.current = (event.clientY - windowHalfYRef.current) * 0.1;
    };

    window.addEventListener('resize', handleResize);
    document.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('mousemove', handleMouseMove);
      if (rendererRef.current) {
        rendererRef.current.dispose();
      }
    };
  }, []);

  function init() {
    windowHalfXRef.current = window.innerWidth / 2;
    windowHalfYRef.current = window.innerHeight / 2;

    // Scene setup
    sceneRef.current = new THREE.Scene();
    sceneRef.current.fog = new THREE.FogExp2(0x000011, 0.0008);

    // Camera setup
    cameraRef.current = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 1, 3000);
    cameraRef.current.position.z = 1000;

    // Create particle system
    createParticles();

    // Create geometric shapes
    createGeometricShapes();

    // Renderer setup
    rendererRef.current = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    rendererRef.current.setSize(window.innerWidth, window.innerHeight);
    rendererRef.current.setClearColor(0x000011, 1);
    rendererRef.current.setPixelRatio(window.devicePixelRatio);
    
    if (containerRef.current) {
      containerRef.current.appendChild(rendererRef.current.domElement);
    }
  }

  function createParticles() {
    if (!sceneRef.current) return;

    const geometry = new THREE.BufferGeometry();
    const vertices: number[] = [];
    const colors: number[] = [];

    const particleCount = 4000;

    for (let i = 0; i < particleCount; i++) {
      // Position in a sphere-like cloud but more spread out
      const r = 1000 + Math.random() * 500;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      
      vertices.push(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      );

      // Colors (blue to purple to pink gradient)
      const color = new THREE.Color();
      const rand = Math.random();
      if (rand < 0.33) color.setHex(0x00d4ff); // blue
      else if (rand < 0.66) color.setHex(0x7c3aed); // purple
      else color.setHex(0xec4899); // pink
      
      colors.push(color.r, color.g, color.b);
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 1.5,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true
    });

    particlesRef.current = new THREE.Points(geometry, material);
    sceneRef.current.add(particlesRef.current);
  }

  function createGeometricShapes() {
    if (!sceneRef.current) return;

    // Create floating geometric shapes
    const shapes = [
      new THREE.TetrahedronGeometry(50, 0),
      new THREE.OctahedronGeometry(40, 0),
      new THREE.IcosahedronGeometry(35, 0),
      new THREE.DodecahedronGeometry(45, 0)
    ];

    shapes.forEach((geometry, index) => {
      const material = new THREE.MeshBasicMaterial({
        color: index % 2 === 0 ? 0x00d4ff : 0x7c3aed,
        wireframe: true,
        transparent: true,
        opacity: 0.3
      });

      const mesh = new THREE.Mesh(geometry, material);
      
      // Random positioning
      mesh.position.set(
        Math.random() * 1000 - 500,
        Math.random() * 1000 - 500,
        Math.random() * 500 - 250
      );

      // Random rotation
      mesh.rotation.set(
        Math.random() * Math.PI,
        Math.random() * Math.PI,
        Math.random() * Math.PI
      );

      geometriesRef.current.push(mesh);
      sceneRef.current!.add(mesh);

      // Animate the shapes
      gsap.to(mesh.rotation, {
        x: mesh.rotation.x + Math.PI * 2,
        y: mesh.rotation.y + Math.PI * 2,
        duration: 20 + Math.random() * 10,
        repeat: -1,
        ease: "none"
      });
    });
  }

  function animate() {
    requestAnimationFrame(animate);

    const time = Date.now() * 0.0005;

    // Rotate particle system slowly
    if (particlesRef.current) {
      particlesRef.current.rotation.y += 0.0005;
      particlesRef.current.rotation.x += 0.0002;
      (particlesRef.current.material as THREE.PointsMaterial).opacity = 0.4 + Math.sin(time) * 0.2;
    }

    // Mouse interaction - smooth parallax
    const targetX = mouseXRef.current * 0.5;
    const targetY = -mouseYRef.current * 0.5;
    
    if (cameraRef.current && sceneRef.current) {
      cameraRef.current.position.x += (targetX - cameraRef.current.position.x) * 0.05;
      cameraRef.current.position.y += (targetY - cameraRef.current.position.y) * 0.05;
      cameraRef.current.lookAt(sceneRef.current.position);
    }

    // Animate geometric shapes with individual behaviors
    geometriesRef.current.forEach((mesh, index) => {
      mesh.rotation.x += 0.001 * (index + 1);
      mesh.rotation.y += 0.002 * (index + 1);
      mesh.position.y += Math.sin(time + index) * 0.2;
    });

    if (rendererRef.current && sceneRef.current && cameraRef.current) {
      rendererRef.current.render(sceneRef.current, cameraRef.current);
    }
  }

  return <div ref={containerRef} className="three-container"></div>;
};

export default ThreeBackground;
