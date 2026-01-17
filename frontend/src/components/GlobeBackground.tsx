import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { gsap } from 'gsap';

interface GlobeBackgroundProps {
  taskTrigger: number; // Increment/Change this to trigger animation
}

const GlobeBackground: React.FC<GlobeBackgroundProps> = ({ taskTrigger }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const globeRef = useRef<THREE.Group | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Cleanup previous scene if exists (though useEffect dependency [] should prevent this)
    if (rendererRef.current) {
        containerRef.current.innerHTML = '';
    }

    init();
    animate();

    const handleResize = () => {
      if (!cameraRef.current || !rendererRef.current) return;
      cameraRef.current.aspect = window.innerWidth / window.innerHeight;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (rendererRef.current) {
        rendererRef.current.dispose();
      }
    };
  }, []);

  // Watch for taskTrigger changes to animate the globe
  useEffect(() => {
    if (globeRef.current) {
        // Pick a random rotation
        const randomLat = (Math.random() - 0.5) * Math.PI; // -90 to 90
        const randomLon = (Math.random() - 0.5) * Math.PI * 4; // Allow multiple spins

        gsap.to(globeRef.current.rotation, {
            x: randomLat,
            y: randomLon,
            duration: 2,
            ease: "power2.inOut"
        });
    }
  }, [taskTrigger]);

  function init() {
    // Scene setup
    sceneRef.current = new THREE.Scene();
    sceneRef.current.fog = new THREE.FogExp2(0x000000, 0.002);

    // Camera setup
    cameraRef.current = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 1000);
    cameraRef.current.position.z = 20;

    // Globe Group
    globeRef.current = new THREE.Group();
    sceneRef.current.add(globeRef.current);

    // 1. Create a wireframe sphere (The "Globe")
    const geometry = new THREE.IcosahedronGeometry(10, 2);
    const material = new THREE.MeshBasicMaterial({ 
        color: 0x4a90e2, 
        wireframe: true, 
        transparent: true, 
        opacity: 0.3 
    });
    const sphere = new THREE.Mesh(geometry, material);
    globeRef.current.add(sphere);

    // 2. Add Partciles (vertices of a more detailed sphere to look like cities/nodes)
    const particleGeo = new THREE.IcosahedronGeometry(10, 4);
    const particleMat = new THREE.PointsMaterial({
        color: 0x00ffff,
        size: 0.1,
        transparent: true,
        opacity: 0.8
    });
    // We only want the vertices
    // However, IcosahedronGeometry is a Mesh geometry. We can create Points from it.
    const particles = new THREE.Points(particleGeo, particleMat);
    globeRef.current.add(particles);

    // 3. Add an inner glowing core
    const coreGeo = new THREE.SphereGeometry(9.5, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({
        color: 0x000033,
        transparent: true,
        opacity: 0.9
    });
    const core = new THREE.Mesh(coreGeo, coreMat);
    globeRef.current.add(core);


    // 4. Ambient Stars
    const starsGeometry = new THREE.BufferGeometry();
    const starsCount = 1000;
    const posArray = new Float32Array(starsCount * 3);
    
    for(let i = 0; i < starsCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 100; // Spread stars around
    }
    
    starsGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const starsMaterial = new THREE.PointsMaterial({
        size: 0.05,
        color: 0xffffff,
        transparent: true,
        opacity: 0.5
    });
    const stars = new THREE.Points(starsGeometry, starsMaterial);
    sceneRef.current.add(stars);


    // Renderer setup
    rendererRef.current = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    rendererRef.current.setSize(window.innerWidth, window.innerHeight);
    rendererRef.current.setPixelRatio(window.devicePixelRatio);
    
    if (containerRef.current) {
      containerRef.current.appendChild(rendererRef.current.domElement);
    }
  }

  function animate() {
    requestAnimationFrame(animate);

    if (globeRef.current) {
        // Constant slow rotation
        globeRef.current.rotation.y += 0.001;
    }

    if (rendererRef.current && sceneRef.current && cameraRef.current) {
      rendererRef.current.render(sceneRef.current, cameraRef.current);
    }
  }

  return (
    <div 
      ref={containerRef} 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none'
      }}
    />
  );
};

export default GlobeBackground;
