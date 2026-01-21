import React, { useEffect, useRef, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { gsap } from 'gsap';
import SectionDataEditor from './SectionDataEditor';
import { chroniclesConfig } from './sectionEditorConfig';
import './TimelineSection.css';

interface TimelineSectionProps {
  timeline: any;
  journey: any;
  sectionIndex: number;
  historyId?: string; // For editing functionality
}

const TimelineSection: React.FC<TimelineSectionProps> = ({ timeline, journey: _journey, sectionIndex: _sectionIndex, historyId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const globeRef = useRef<THREE.Group | null>(null);
  const timelineGroupRef = useRef<THREE.Group | null>(null);
  const markersRef = useRef<THREE.Mesh[]>([]);
  const controlsRef = useRef<OrbitControls | null>(null);
  const [activeEvent, setActiveEvent] = useState<any | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState(timeline?.events || []);
  
  // Data processing - Sort events chronologically (oldest to newest)
  // so they appear from bottom to top on the spiral
  const events = useMemo(() => {
    const eventsWithIndex = timelineEvents?.map((e: any, i: number) => ({ ...e, originalIndex: i })) || [];
    // Sort by date (start_date or date field)
    return eventsWithIndex.sort((a: any, b: any) => {
      const dateA = new Date(a.start_date || a.date).getTime();
      const dateB = new Date(b.start_date || b.date).getTime();
      return dateA - dateB; // Ascending order (oldest first)
    });
  }, [timelineEvents]);

  // Update local events when timeline prop changes
  useEffect(() => {
    setTimelineEvents(timeline?.events || []);
  }, [timeline]);

  // Handler for events update from modal
  const handleEventsUpdate = (updatedEvents: any[]) => {
    setTimelineEvents(updatedEvents);
    setActiveEvent(null); // Close any open event popup
  };

  // Handler to open edit modal
  const handleOpenEditModal = () => {
    setIsEditModalOpen(true);
    setActiveEvent(null); // Close any open event popup
  };

  useEffect(() => {
    if (!containerRef.current || events.length === 0) return;

    // --- Init Scene ---
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.fog = new THREE.FogExp2(0x000000, 0.015); // Slightly lighter fog for visibility

    const camera = new THREE.PerspectiveCamera(60, containerRef.current.clientWidth / containerRef.current.clientHeight, 0.1, 1000);
    camera.position.z = 45; // Moved back for larger globe
    camera.position.y = 15;
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.innerHTML = '';
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // --- Controls ---
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = false;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.8;
    controls.minDistance = 30;
    controls.maxDistance = 60;
    controlsRef.current = controls;

    // --- Lights ---
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);
    const pointLight = new THREE.PointLight(0x00ffff, 2, 120);
    pointLight.position.set(30, 30, 30);
    scene.add(pointLight);

    // --- Globe ---
    const globeGroup = new THREE.Group();
    scene.add(globeGroup);
    globeRef.current = globeGroup;

    // 1. Wireframe Sphere (Larger)
    const geometry = new THREE.IcosahedronGeometry(15, 2); // Increased from 10
    const material = new THREE.MeshBasicMaterial({ 
      color: 0x4a90e2, 
      wireframe: true, 
      transparent: true, 
      opacity: 0.1
    });
    const sphere = new THREE.Mesh(geometry, material);
    globeGroup.add(sphere);

    // 2. Core (Larger)
    const coreGeo = new THREE.SphereGeometry(14.8, 32, 32); // Increased from 9.8
    const coreMat = new THREE.MeshBasicMaterial({ color: 0x050510, transparent: true, opacity: 0.85 }); 
    const core = new THREE.Mesh(coreGeo, coreMat);
    globeGroup.add(core);

    // 3. Particles
    const particlesGeo = new THREE.BufferGeometry();
    const particleCount = 2000;
    const posArray = new Float32Array(particleCount * 3);
    for(let i = 0; i < particleCount * 3; i++) {
      posArray[i] = (Math.random() - 0.5) * 40; // Increased spread
    }
    particlesGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particlesMat = new THREE.PointsMaterial({
      size: 0.08,
      color: 0x88ccff,
      transparent: true,
      opacity: 0.4
    });
    const starField = new THREE.Points(particlesGeo, particlesMat);
    scene.add(starField);

    // --- Timeline Spiral Path ---
    const timelineGroup = new THREE.Group();
    globeGroup.add(timelineGroup);
    timelineGroupRef.current = timelineGroup;

    const curvePoints: THREE.Vector3[] = [];
    const radius = 16.5; // Increased from 11
    const loops = 3.5;

    // Generate Spiral
    for (let i = 0; i <= 120; i++) {
        const t = i / 120;
        const theta = t * loops * Math.PI * 2;
        
        // Spherical Spiral:
        const phi = THREE.MathUtils.lerp(Math.PI * 0.15, Math.PI * 0.85, t);
        const spiralRadius = radius; 
        
        const x = spiralRadius * Math.sin(phi) * Math.cos(theta);
        const z = spiralRadius * Math.sin(phi) * Math.sin(theta);
        const yPos = spiralRadius * Math.cos(phi); 
        
        curvePoints.push(new THREE.Vector3(x, yPos, z));
    }

    const curve = new THREE.CatmullRomCurve3(curvePoints);
    const tubeGeo = new THREE.TubeGeometry(curve, 150, 0.08, 8, false);
    const tubeMat = new THREE.MeshBasicMaterial({ color: 0xefefef, transparent: true, opacity: 0.2 });
    const tube = new THREE.Mesh(tubeGeo, tubeMat);
    timelineGroup.add(tube);

    // --- Place Event Markers & Labels ---
    markersRef.current = [];
    
    // Icon name to emoji mapper
    const iconMap: { [key: string]: string } = {
      'briefcase': '💼',
      'graduation-cap': '🎓',
      'trophy': '🏆',
      'code': '💻',
      'certificate': '📜',
      'star': '⭐',
      'rocket': '🚀',
      'book': '📚',
      'lightbulb': '💡',
      'heart': '❤️',
      'flag': '🚩',
      'target': '🎯',
      'medal': '🏅',
      'crown': '👑',
      'fire': '🔥'
    };
    
    // Date formatter helper
    const formatEventDate = (event: any): string => {
        const date = new Date(event.start_date || event.date);
        const year = date.getFullYear();
        
        // Get icon - check if it's already an emoji or needs mapping
        let iconStr = '';
        if (event.icon) {
          // If it's already an emoji (single character or emoji), use it
          if (event.icon.length <= 2 || /\p{Emoji}/u.test(event.icon)) {
            iconStr = event.icon;
          } else {
            // Try to map the icon name to emoji
            iconStr = iconMap[event.icon] || iconMap[event.icon.toLowerCase()] || '';
          }
        }
        
        // Check if we have a valid month (not just a year)
        const hasMonth = date.getMonth() !== 0 || date.getDate() !== 1 || 
                        (event.start_date || event.date).includes('-');
        
        if (hasMonth) {
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const month = monthNames[date.getMonth()];
            const dateStr = `${month} ${year}`;
            
            // Add icon if available
            return iconStr ? `${iconStr} ${dateStr}` : dateStr;
        } else {
            // Only year available
            return iconStr ? `${iconStr} ${year}` : `${year}`;
        }
    };
    
    // Label Helper
    const createLabel = (text: string) => {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 512;
        canvas.height = 128;
        if(context) {
            context.fillStyle = 'rgba(0,0,0,0)'; // Transparent
            context.fillRect(0, 0, 512, 128);
            // Use system fonts with emoji support
            context.font = 'Bold 40px -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple Color Emoji", "Segoe UI Emoji", Arial, sans-serif';
            context.fillStyle = '#efefef';
            context.textAlign = 'center';
            context.fillText(text, 256, 80);
        }
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.scale.set(8, 2, 1);
        return sprite;
    };

    events.forEach((event: any, index: number) => {
        const t = index / (events.length - 1 || 1);
        const point = curve.getPoint(t);
        
        // Marker
        const markerGeo = new THREE.SphereGeometry(0.5, 16, 16);
        const markerMat = new THREE.MeshBasicMaterial({ color: 0x999999 });
        const marker = new THREE.Mesh(markerGeo, markerMat);
        
        marker.position.copy(point);
        marker.userData = { id: index, event: event };
        marker.name = 'timeline-marker';
        
        timelineGroup.add(marker);
        markersRef.current.push(marker);

        // Glow
        const ringGeo = new THREE.RingGeometry(0.6, 0.8, 32);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide, transparent: true, opacity: 0.6 });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.position.copy(point);
        ring.lookAt(point.clone().multiplyScalar(2));
        timelineGroup.add(ring);

        // Label (Icon + Month Year or just Year)
        const dateStr = formatEventDate(event);
        const label = createLabel(dateStr);
        // Position label slightly "out" from the marker
        const labelPos = point.clone().normalize().multiplyScalar(radius + 2);
        label.position.copy(labelPos);
        timelineGroup.add(label);
    });

    // --- Interaction ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerMove = (event: MouseEvent) => {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(timelineGroup.children);
        
        let found = false;
        if (intersects.length > 0) {
            for (let i = 0; i < intersects.length; i++) {
                if (intersects[i].object.name === 'timeline-marker') {
                    document.body.style.cursor = 'pointer';
                    found = true;
                    // Hover effect
                    gsap.to(intersects[i].object.scale, { x: 1.8, y: 1.8, z: 1.8, duration: 0.3 });
                    // Pause auto rotation on hover
                    controls.autoRotate = false;
                }
            }
        }
        
        if (!found) {
            document.body.style.cursor = 'grab'; // Default orbit control cursor
            controls.autoRotate = true;
            markersRef.current.forEach(m => {
                gsap.to(m.scale, { x: 1, y: 1, z: 1, duration: 0.3 });
            });
        }
    };

    const onPointerDown = () => {
        document.body.style.cursor = 'grabbing';
    };

    const onClick = (event: MouseEvent) => {
        // Simple raycast click detection
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(timelineGroup.children);
        
        for (let i = 0; i < intersects.length; i++) {
            if (intersects[i].object.userData.event) {
                setActiveEvent(intersects[i].object.userData.event);
                
                // Focus camera on this event
                // Stop rotation to allow reading
                controls.autoRotate = false;
                
                // Optional: Snap camera?
                // For now, let OrbitControls handle view, just show popup
                break;
            }
        }
    };

    // Listeners
    if (containerRef.current) {
        // OrbitControls handles most drag, but we want click detection
        // We attach click to the container
    }
    
    // Add event listeners to window or container
    // Container is better for specific component interaction
    const container = containerRef.current;
    container.addEventListener('mousemove', onPointerMove);
    container.addEventListener('mousedown', onPointerDown);
    container.addEventListener('click', onClick);

    const animate = () => {
      requestAnimationFrame(animate);
      controls.update(); // Required for autoRotate and damping
      starField.rotation.y -= 0.0003;
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
        if (!containerRef.current || !camera || !renderer) return;
        camera.aspect = containerRef.current.clientWidth / containerRef.current.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousemove', onPointerMove);
      container.removeEventListener('mousedown', onPointerDown);
      container.removeEventListener('click', onClick);
      if (containerRef.current) containerRef.current.innerHTML = '';
      renderer.dispose();
      controls.dispose();
    };
  }, [events]);

  return (
    <section className="journey-section timeline-section" style={{ height: '100vh', position: 'relative', overflow: 'hidden' }} data-section={_sectionIndex}>
      <div 
        ref={containerRef} 
        style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, zIndex: 1, outline: 'none' }}
      />
      
      {/* Title Overlay */}
      <div className="timeline-title-overlay" style={{ position: 'absolute', top: '5%', left: '50%', transform: 'translateX(-50%)', zIndex: 2, pointerEvents: 'none', textAlign: 'center', width: '90%' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', pointerEvents: 'auto' }}>
          <h2 className="section-title gradient-text" style={{ fontSize: '2.5rem', textShadow: '0 2px 10px rgba(0,0,0,0.5)', margin: 0 }}>
            Chronicles
          </h2>
          {historyId && (
            <button
              onClick={handleOpenEditModal}
              className="edit-section-btn"
              title="Edit Chronicles"
              style={{
                background: 'rgba(0, 212, 255, 0.15)',
                border: '1px solid rgba(0, 212, 255, 0.3)',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
                color: '#00d4ff',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(0, 212, 255, 0.25)';
                e.currentTarget.style.transform = 'scale(1.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(0, 212, 255, 0.15)';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m18 2 4 4-5.5 5.5-4-4L18 2z"></path>
                <path d="M11.5 6.5 6 12v4h4l5.5-5.5"></path>
              </svg>
            </button>
          )}
        </div>
        <p className="section-subtitle" style={{ fontSize: '1rem', opacity: 0.8, marginBottom: '3rem' }}>Drag to explore • Tap nodes for details</p>
      </div>

      {/* Details Popup */}
      <AnimatePresence>
        {activeEvent && (
          <motion.div 
            className="timeline-detail-popup glass"
            initial={{ opacity: 0, scale: 0.5, y: 50, borderRadius: '50%' }}
            animate={{ opacity: 1, scale: 1, y: 0, borderRadius: '16px' }}
            exit={{ opacity: 0, scale: 0.5, y: 20, borderRadius: '50%' }}
            transition={{ type: "spring", damping: 45, stiffness: 100 }}
            style={{
                position: 'absolute',
                top: '0%',
                left: 'auto',
                transform: 'translate(0%, auto)',
                width: '85%',
                maxWidth: '450px',
                padding: '2.5rem',
                zIndex: 10,
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(80, 200, 255, 0.25)',
                boxShadow: '0 10px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(0, 200, 255, 0.1)',
                backdropFilter: 'blur(12px) saturate(180%)',
                WebkitBackdropFilter: 'blur(12px) saturate(180%)',
            }}
          >
            <button 
                onClick={(e) => { e.stopPropagation(); setActiveEvent(null); }}
                style={{ 
                    position: 'absolute', top: '15px', right: '15px', 
                    background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '50%',
                    width: '30px', height: '30px',
                    color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}
            >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
            <div className="event-date" style={{ color: '#00ffff', fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.5rem' }}>
                {new Date(activeEvent.start_date || activeEvent.date).getFullYear()}
            </div>
            <h3 style={{ fontSize: '1.8rem', fontWeight: '700', marginBottom: '1rem', background: 'linear-gradient(to right, #fff, #88ccff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                {activeEvent.title || activeEvent.name}
            </h3>
            <p style={{ lineHeight: 1.7, color: '#d0d0d0', fontSize: '1rem' }}>
                {activeEvent.description || activeEvent.content}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Section Data Editor - Generic modal for Chronicles/Timeline editing */}
      <SectionDataEditor
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        config={chroniclesConfig}
        items={timelineEvents}
        historyId={historyId || ''}
        onItemsUpdate={handleEventsUpdate}
      />
    </section>
  );
};

export default TimelineSection;
