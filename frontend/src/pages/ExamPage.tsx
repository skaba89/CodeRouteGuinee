/**
 * ExamPage — Interface d'examen CodeRoute Guinée
 * Niveau iCode / En Voiture Simone — timer bloquant, grille de navigation,
 * media illustratif, correction détaillée.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchWithAuth } from '../authClient';
import { useAuthSession } from '../authSession';

const API = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/api\/v1\/?$/, '');

// ── Types ────────────────────────────────────────────────────────────────

interface ExamQuestion {
  id: string;
  number: number;
  category: string;
  text: string;
  options: string[];
  media_type?: 'image' | 'video' | 'svg' | null;
  media_url?: string | null;
  media_alt?: string | null;
  // Disponibles seulement après soumission (dans /results)
  given_answer?: string;
  correct_answer?: string;
  is_correct?: boolean;
  explanation?: string;
}

interface ExamStatus {
  attempt_id: string;
  status: string;
  remaining_seconds: number;
  elapsed_seconds: number;
  total_seconds: number;
  question_count: number;
  score?: number;
  passed?: boolean;
  expired: boolean;
}

interface ExamResult {
  attempt_id: string;
  candidate_name: string;
  score: number;
  total: number;
  score_percent: number;
  passed: boolean;
  threshold: number;
  submitted_at: string;
  questions: ExamQuestion[];
}

// ── SVG illustrations pour les questions démo ─────────────────────────────

function SignSvg({ type }: { type: string }) {
  const signs: Record<string, JSX.Element> = {
    stop: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,5 105,30 115,75 90,112 30,112 5,75 15,30" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
        <text x="60" y="68" textAnchor="middle" fill="#fff" fontSize="20" fontWeight="bold" fontFamily="Arial">STOP</text>
      </svg>
    ),
    priority: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,5 115,115 5,115" fill="#fff" stroke="#e67e22" strokeWidth="6"/>
        <polygon points="60,22 100,100 20,100" fill="#e67e22"/>
        <circle cx="60" cy="82" r="6" fill="#fff"/>
        <rect x="56" y="42" width="8" height="28" rx="4" fill="#fff"/>
      </svg>
    ),
    no_entry: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
        <rect x="20" y="50" width="80" height="20" rx="4" fill="#fff"/>
      </svg>
    ),
    speed_50: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
        <text x="60" y="72" textAnchor="middle" fill="#1a1a2e" fontSize="32" fontWeight="bold" fontFamily="Arial">50</text>
      </svg>
    ),
    roundabout: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
        <circle cx="60" cy="60" r="22" fill="none" stroke="#fff" strokeWidth="5"/>
        <path d="M38 60 Q38 38 60 38" fill="none" stroke="#fff" strokeWidth="5" markerEnd="url(#arr)"/>
        <defs><marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#fff"/></marker></defs>
      </svg>
    ),
    pedestrian: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,5 115,115 5,115" fill="#fff" stroke="#c0392b" strokeWidth="6"/>
        <circle cx="60" cy="48" r="8" fill="#1a1a2e"/>
        <path d="M60 56 L52 80 M60 56 L68 80 M52 80 L48 96 M52 80 L60 96" stroke="#1a1a2e" strokeWidth="3" fill="none"/>
      </svg>
    ),
    give_way: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,115 5,15 115,15" fill="#fff" stroke="#c0392b" strokeWidth="6"/>
        <polygon points="60,100 18,28 102,28" fill="#fff" stroke="#c0392b" strokeWidth="4"/>
      </svg>
    ),
    mandatory: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
        <path d="M30 60 L90 60 M75 45 L90 60 L75 75" stroke="#fff" strokeWidth="8" fill="none" strokeLinecap="round"/>
      </svg>
    ),
  };
  return (
    <div style={{ width: 120, height: 120, margin: '0 auto' }}>
      {signs[type] ?? signs.priority}
    </div>
  );
}

function IntersectionSvg({ type }: { type: string }) {
  if (type === 'priority_right') {
    return (
      <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 320, display: 'block', margin: '0 auto' }}>
        {/* Route principale */}
        <rect x="0" y="85" width="200" height="30" fill="#555"/>
        <rect x="85" y="0" width="30" height="200" fill="#555"/>
        {/* Lignes centrales */}
        <line x1="0" y1="100" x2="80" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        <line x1="120" y1="100" x2="200" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        <line x1="100" y1="0" x2="100" y2="80" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        <line x1="100" y1="120" x2="100" y2="200" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        {/* Voiture A — vient de gauche */}
        <rect x="18" y="90" width="36" height="20" rx="4" fill="#3498db"/>
        <text x="36" y="104" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">A</text>
        {/* Flèche A → droite */}
        <path d="M56 100 L72 100" stroke="#3498db" strokeWidth="2" markerEnd="url(#arrowB)"/>
        {/* Voiture B — vient du bas (droite de A) */}
        <rect x="90" y="148" width="20" height="36" rx="4" fill="#e74c3c"/>
        <text x="100" y="170" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">B</text>
        {/* Flèche B → haut */}
        <path d="M100 146 L100 126" stroke="#e74c3c" strokeWidth="2" markerEnd="url(#arrowR)"/>
        <defs>
          <marker id="arrowB" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#3498db"/></marker>
          <marker id="arrowR" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#e74c3c"/></marker>
        </defs>
        <text x="100" y="192" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">B est à droite de A → B prioritaire</text>
      </svg>
    );
  }
  if (type === 'roundabout') {
    return (
      <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 320, display: 'block', margin: '0 auto' }}>
        <rect width="200" height="200" fill="#222"/>
        <rect x="0" y="85" width="58" height="30" fill="#555"/>
        <rect x="142" y="85" width="58" height="30" fill="#555"/>
        <rect x="85" y="0" width="30" height="58" fill="#555"/>
        <rect x="85" y="142" width="30" height="58" fill="#555"/>
        <circle cx="100" cy="100" r="46" fill="#555"/>
        <circle cx="100" cy="100" r="32" fill="#2c3e50"/>
        <circle cx="100" cy="100" r="24" fill="#27ae60"/>
        <path d="M100 54 A46 46 0 1 1 54 100" fill="none" stroke="#f1c40f" strokeWidth="3" strokeDasharray="8,5" markerEnd="url(#rArr)"/>
        <rect x="12" y="90" width="30" height="20" rx="4" fill="#e74c3c"/>
        <text x="27" y="104" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">Entre</text>
        <rect x="92" y="150" width="16" height="28" rx="3" fill="#3498db"/>
        <text x="100" y="168" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">GIR</text>
        <defs><marker id="rArr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#f1c40f"/></marker></defs>
      </svg>
    );
  }
  return null;
}

function SituationSvg({ type }: { type: string }) {
  if (type === 'overtake_forbidden') {
    return (
      <svg viewBox="0 0 280 160" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 400, display: 'block', margin: '0 auto' }}>
        <rect width="280" height="160" fill="#1a2e1a"/>
        <rect x="0" y="70" width="280" height="60" fill="#3d3d3d"/>
        <rect x="0" y="98" width="280" height="4" fill="#fff"/>
        <rect x="0" y="68" width="280" height="4" fill="#fff"/>
        {/* Ligne continue = dépassement interdit */}
        <rect x="0" y="97" width="280" height="3" fill="#fff"/>
        {/* Virage = danger */}
        <path d="M0 130 Q140 40 280 130" stroke="#333" strokeWidth="60" fill="none"/>
        <path d="M0 130 Q140 40 280 130" stroke="#3d3d3d" strokeWidth="52" fill="none"/>
        {/* Voitures */}
        <rect x="40" y="75" width="48" height="22" rx="5" fill="#3498db"/>
        <rect x="44" y="79" width="18" height="10" rx="2" fill="#85c1e9"/>
        <rect x="104" y="75" width="48" height="22" rx="5" fill="#e74c3c"/>
        <text x="64" y="90" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
        <text x="128" y="90" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">CAMION</text>
        {/* Croix interdiction */}
        <circle cx="200" cy="40" r="20" fill="rgba(192,57,43,0.9)"/>
        <path d="M190 30 L210 50 M210 30 L190 50" stroke="#fff" strokeWidth="4" strokeLinecap="round"/>
        <text x="200" y="70" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">Interdit</text>
      </svg>
    );
  }
  if (type === 'safe_distance') {
    return (
      <svg viewBox="0 0 300 120" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 420, display: 'block', margin: '0 auto' }}>
        <rect width="300" height="120" fill="#1a2e1a"/>
        <rect x="0" y="50" width="300" height="50" fill="#3d3d3d"/>
        <line x1="0" y1="75" x2="300" y2="75" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
        <rect x="10" y="55" width="56" height="28" rx="5" fill="#3498db"/>
        <text x="38" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
        <rect x="180" y="55" width="56" height="28" rx="5" fill="#e74c3c"/>
        <text x="208" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">DEVANT</text>
        {/* Distance */}
        <line x1="68" y1="80" x2="178" y2="80" stroke="#27ae60" strokeWidth="2"/>
        <line x1="68" y1="74" x2="68" y2="86" stroke="#27ae60" strokeWidth="2"/>
        <line x1="178" y1="74" x2="178" y2="86" stroke="#27ae60" strokeWidth="2"/>
        <text x="123" y="100" textAnchor="middle" fill="#27ae60" fontSize="11" fontWeight="bold">≥ 2 secondes</text>
        <text x="123" y="112" textAnchor="middle" fill="#aaa" fontSize="9">≈ 50 m à 90 km/h</text>
      </svg>
    );
  }
  if (type === 'emergency_vehicle') {
    return (
      <svg viewBox="0 0 280 140" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 400, display: 'block', margin: '0 auto' }}>
        <rect width="280" height="140" fill="#0d1117"/>
        <rect x="0" y="60" width="280" height="50" fill="#3d3d3d"/>
        <rect x="0" y="110" width="280" height="4" fill="#fff"/>
        <rect x="0" y="58" width="280" height="4" fill="#fff"/>
        <line x1="0" y1="84" x2="280" y2="84" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
        {/* Voitures qui se rangent */}
        <rect x="20" y="88" width="48" height="20" rx="4" fill="#3498db" opacity="0.7"/>
        <rect x="210" y="88" width="48" height="20" rx="4" fill="#2ecc71" opacity="0.7"/>
        {/* Ambulance */}
        <rect x="110" y="65" width="60" height="28" rx="5" fill="#fff"/>
        <rect x="113" y="68" width="22" height="12" rx="2" fill="#85c1e9"/>
        <text x="140" y="82" textAnchor="middle" fill="#c0392b" fontSize="11" fontWeight="bold">🚑 SAMU</text>
        {/* Gyrophare */}
        <circle cx="140" cy="63" r="5" fill="#c0392b" opacity="0.9"/>
        <circle cx="140" cy="63" r="10" fill="rgba(192,57,43,0.3)"/>
        {/* Flèches se ranger */}
        <path d="M44 84 L24 84" stroke="#3498db" strokeWidth="2" markerEnd="url(#aL)"/>
        <path d="M236 84 L256 84" stroke="#2ecc71" strokeWidth="2" markerEnd="url(#aR)"/>
        <defs>
          <marker id="aL" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#3498db"/></marker>
          <marker id="aR" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#2ecc71"/></marker>
        </defs>
        <text x="140" y="130" textAnchor="middle" fill="#f1c40f" fontSize="10" fontWeight="bold">Se dégager immédiatement → priorité absolue</text>
      </svg>
    );
  }
  return null;
}

// ── Banque de 40 questions illustrées ─────────────────────────────────────

function buildDemoQuestions(): ExamQuestion[] {
  return [
    {id:'q01',number:1,category:'Signalisation',text:"Quel est ce panneau et que vous impose-t-il ?",options:["Ralentir et passer prudemment","S'arrêter complètement, céder le passage","Klaxonner pour signaler votre présence","Accélérer pour dégager l'intersection"],correct_answer:"S'arrêter complètement, céder le passage",media_type:'svg',media_url:'stop',media_alt:'Panneau STOP rouge octogonal',explanation:'Le STOP impose un arrêt complet (roues immobiles) puis une cession de priorité.'},
    {id:'q02',number:2,category:'Signalisation',text:"Ce panneau est installé avant votre voie. Que signifie-t-il ?",options:["Vous avez la priorité","Vous devez céder le passage aux véhicules sur la route principale","Danger de virage à droite","Fin de zone de travaux"],correct_answer:"Vous devez céder le passage aux véhicules sur la route principale",media_type:'svg',media_url:'give_way',media_alt:'Panneau cédez le passage — triangle inversé rouge et blanc',explanation:'Le triangle inversé signifie cédez le passage — vous devez laisser passer les véhicules sur la voie principale.'},
    {id:'q03',number:3,category:'Signalisation',text:"Quelle est la vitesse maximale que vous pouvez atteindre ici ?",options:["30 km/h","50 km/h","60 km/h","70 km/h"],correct_answer:"50 km/h",media_type:'svg',media_url:'speed_50',media_alt:'Panneau de limitation de vitesse à 50 km/h',explanation:'Le panneau circulaire rouge avec 50 impose une vitesse maximale de 50 km/h à partir de ce point.'},
    {id:'q04',number:4,category:'Signalisation',text:"Vous approchez de ce panneau. Que devez-vous faire impérativement ?",options:["Ralentir et klaxonner","Vous arrêter — accès totalement interdit","Passer si votre véhicule est petit","Céder le passage à droite"],correct_answer:"Vous arrêter — accès totalement interdit",media_type:'svg',media_url:'no_entry',media_alt:'Panneau sens interdit — rond rouge avec barre blanche',explanation:'Le panneau sens interdit interdit tout accès. Vous ne pouvez pas vous engager dans cette voie.'},
    {id:'q05',number:5,category:'Signalisation',text:"Vous entrez dans un giratoire. Ce panneau est à l'entrée. Que signifie-t-il ?",options:["Vous avez la priorité sur les voitures dans le rond-point","Vous devez céder le passage aux véhicules circulant dans le giratoire","Sens obligatoire pour les camions","Vitesse maximale de 20 km/h dans le giratoire"],correct_answer:"Vous devez céder le passage aux véhicules circulant dans le giratoire",media_type:'svg',media_url:'roundabout',media_alt:'Panneau giratoire — rond bleu avec flèche circulaire',explanation:'À l'entrée d'un giratoire, vous devez toujours céder le passage aux véhicules déjà engagés.'},
    {id:'q06',number:6,category:'Priorités',text:"Dans cette situation, quelle voiture est prioritaire ?",options:["La voiture A (venant de gauche)","La voiture B (venant du bas, à droite de A)","Les deux arrivent ensemble — ni l'une ni l'autre","La voiture la plus rapide"],correct_answer:"La voiture B (venant du bas, à droite de A)",media_type:'svg',media_url:'intersection_priority_right',media_alt:'Intersection sans signalisation — voiture A vient de gauche, voiture B vient du bas',explanation:'Sans signalisation, la priorité à droite s'applique. B arrive par la droite de A → B est prioritaire.'},
    {id:'q07',number:7,category:'Priorités',text:"Qui a la priorité dans cette scène de giratoire ?",options:["La voiture qui entre (rouge)","La voiture déjà dans le giratoire (bleue)","Le véhicule le plus grand","Celui qui a le clignotant activé"],correct_answer:"La voiture déjà dans le giratoire (bleue)",media_type:'svg',media_url:'intersection_roundabout',media_alt:'Giratoire — voiture entrant vs voiture circulant à l'intérieur',explanation:'Les véhicules circulant dans le giratoire ont toujours la priorité sur ceux qui entrent.'},
    {id:'q08',number:8,category:'Priorités',text:"Un SAMU avec gyrophare et sirène approche dans votre dos. Que faites-vous ?",options:["Maintenez votre vitesse pour ne pas le gêner","Serrez à droite dès que possible, ralentissez, laissez-le passer","Klaxonnez pour avertir les autres conducteurs","Ignorez-le sur les routes secondaires"],correct_answer:"Serrez à droite dès que possible, ralentissez, laissez-le passer",media_type:'svg',media_url:'situation_emergency_vehicle',media_alt:'Ambulance avec gyrophare dépassant des voitures qui se dégagent',explanation:'Les véhicules d'urgence en intervention ont priorité absolue. Dégagez-vous immédiatement.'},
    {id:'q09',number:9,category:'Priorités',text:"À un passage à niveau non gardé sans barrières, vous devez :",options:["Traverser rapidement sans vous arrêter","Marquer l'arrêt obligatoire, regarder des deux côtés, traverser vite","Klaxonner et traverser en accélérant","Céder uniquement si vous entendez le train"],correct_answer:"Marquer l'arrêt obligatoire, regarder des deux côtés, traverser vite",explanation:'L'arrêt est obligatoire aux passages à niveau non gardés. Vérifiez de chaque côté avant de traverser.'},
    {id:'q10',number:10,category:'Vitesse',text:"Quelle distance de sécurité devez-vous respecter avec le véhicule devant vous ?",options:["Une distance fixe de 10 mètres","La distance parcourue en 2 secondes minimum","La longueur de votre voiture","5 mètres en ville, 10 mètres sur route"],correct_answer:"La distance parcourue en 2 secondes minimum",media_type:'svg',media_url:'situation_safe_distance',media_alt:'Deux voitures sur autoroute avec indication de la distance de sécurité de 2 secondes',explanation:'La règle des 2 secondes s'adapte à la vitesse : à 90 km/h, cela correspond à environ 50 mètres.'},
    {id:'q11',number:11,category:'Vitesse',text:"Quelle est la vitesse maximale autorisée en agglomération en Guinée (sauf panneau contraire) ?",options:["40 km/h","50 km/h","60 km/h","70 km/h"],correct_answer:"50 km/h",explanation:'La limite légale en agglomération est de 50 km/h conformément à la réglementation guinéenne.'},
    {id:'q12',number:12,category:'Vitesse',text:"Sur route nationale hors agglomération, la vitesse maximale est :",options:["80 km/h","90 km/h","100 km/h","110 km/h"],correct_answer:"90 km/h",explanation:'La limite hors agglomération sur route nationale est de 90 km/h en Guinée.'},
    {id:'q13',number:13,category:'Vitesse',text:"Par pluie battante réduisant la visibilité, vous devez :",options:["Maintenir votre vitesse habituelle","Réduire votre vitesse et augmenter vos distances de sécurité","Allumer les feux de route et maintenir la vitesse","Doubler la distance de freinage et rien d'autre"],correct_answer:"Réduire votre vitesse et augmenter vos distances de sécurité",explanation:'La pluie réduit l'adhérence et la visibilité. Réduire la vitesse et augmenter les distances est impératif.'},
    {id:'q14',number:14,category:'Vitesse',text:"La distance d'arrêt d'un véhicule à 90 km/h sur route sèche est d'environ :",options:["30 mètres","50 mètres","75 mètres","120 mètres"],correct_answer:"75 mètres",explanation:'À 90 km/h : ≈25 m de réaction (1 s) + ≈50 m de freinage = 75 m sur route sèche.'},
    {id:'q15',number:15,category:'Dépassement',text:"Dans cette scène, devez-vous dépasser le camion ?",options:["Oui, la voie en face semble libre","Non — ligne continue et virage = dépassement interdit","Oui si vous klaxonnez d'abord","Oui si vous roulez vite"],correct_answer:"Non — ligne continue et virage = dépassement interdit",media_type:'svg',media_url:'situation_overtake_forbidden',media_alt:'Route avec virage, ligne blanche continue et camion devant',explanation:'La ligne continue + le virage interdisent formellement tout dépassement dans cette zone.'},
    {id:'q16',number:16,category:'Dépassement',text:"Avant de dépasser, vous devez vérifier (choisissez la réponse complète) :",options:["Que votre klaxon fonctionne","Que la voie opposée est libre, que le dépassement est autorisé, que vous pouvez finir avant un obstacle","Que le conducteur devant vous vous a vu","Que vous avez assez de carburant"],correct_answer:"Que la voie opposée est libre, que le dépassement est autorisé, que vous pouvez finir avant un obstacle",explanation:'Un dépassement mal préparé est la cause de nombreux accidents graves. Les trois vérifications sont indispensables.'},
    {id:'q17',number:17,category:'Dépassement',text:"Vous souhaitez tourner à gauche. Quelle est la séquence correcte ?",options:["Tourner directement sans signal","Signaler, se placer à gauche, ralentir, vérifier les rétroviseurs puis tourner","Klaxonner et tourner rapidement","Attendre que tous les véhicules s'arrêtent"],correct_answer:"Signaler, se placer à gauche, ralentir, vérifier les rétroviseurs puis tourner",explanation:'Toute manœuvre exige : signal suffisamment tôt, positionnement correct, réduction de vitesse, vérification.'},
    {id:'q18',number:18,category:'Signalisation',text:"Une ligne blanche continue au sol signifie :",options:["On peut la franchir si la voie est libre","Il est interdit de la franchir ou de la chevaucher","Zone de stationnement autorisé","Fin de voie prioritaire"],correct_answer:"Il est interdit de la franchir ou de la chevaucher",explanation:'La ligne continue est absolument infranchissable — aucun dépassement ni changement de file n'est permis.'},
    {id:'q19',number:19,category:'Signalisation',text:"Un feu orange clignotant à une intersection vous indique :",options:["Arrêt obligatoire","Passage libre sans précaution","Ralentir et traverser prudemment","Priorité à droite"],correct_answer:"Ralentir et traverser prudemment",explanation:'Le feu orange clignotant signale un carrefour dangereux : traversez lentement en vous assurant que la voie est dégagée.'},
    {id:'q20',number:20,category:'Signalisation',text:"Ce panneau vous oblige à :",options:["Céder le passage","Tourner à droite uniquement","Aller tout droit — direction obligatoire","Maintenir votre vitesse"],correct_answer:"Aller tout droit — direction obligatoire",media_type:'svg',media_url:'mandatory',media_alt:'Panneau rond bleu avec flèche blanche indiquant direction obligatoire tout droit',explanation:'Le panneau circulaire bleu à flèche impose la direction indiquée. Vous devez aller tout droit.'},
    {id:'q21',number:21,category:'Signalisation',text:"Ce panneau triangulaire rouge avec point d'exclamation signifie :",options:["Travaux sur chaussée","Danger non spécifié — vigilance requise","Priorité à droite","Zone scolaire"],correct_answer:"Danger non spécifié — vigilance requise",media_type:'svg',media_url:'priority',media_alt:'Panneau triangulaire rouge avec point d'exclamation',explanation:'Ce triangle avertit d'un danger dont la nature n'est pas précisée. Soyez vigilant et adaptez votre vitesse.'},
    {id:'q22',number:22,category:'Signalisation',text:"Un panneau octogonal rouge avec STOP m'impose :",options:["Ralentir fortement","Céder le passage uniquement si un véhicule arrive","Arrêt complet obligatoire puis priorité aux véhicules sur la voie principale","Klaxonner avant de passer"],correct_answer:"Arrêt complet obligatoire puis priorité aux véhicules sur la voie principale",media_type:'svg',media_url:'stop',media_alt:'Panneau STOP',explanation:'Le STOP impose un arrêt complet (roues immobiles) avant la ligne. Ensuite, céder le passage.'},
    {id:'q23',number:23,category:'Sécurité',text:"Le port de la ceinture de sécurité est :",options:["Obligatoire uniquement sur les routes nationales","Obligatoire pour tous les occupants en toutes circonstances","Conseillé mais pas obligatoire en ville","Obligatoire seulement pour le conducteur"],correct_answer:"Obligatoire pour tous les occupants en toutes circonstances",explanation:'La ceinture est obligatoire pour TOUS les occupants (avant et arrière) dès que le véhicule est en mouvement.'},
    {id:'q24',number:24,category:'Sécurité',text:"À quelle distance devez-vous placer votre triangle de signalisation ?",options:["5 mètres","Juste derrière le véhicule","30 mètres minimum, davantage sur route rapide","100 mètres exactement"],correct_answer:"30 mètres minimum, davantage sur route rapide",explanation:'Le triangle se place à 30 m minimum. Sur route rapide ou à mauvaise visibilité, plus loin pour avertir à temps.'},
    {id:'q25',number:25,category:'Sécurité',text:"L'usage du téléphone tenu en main en conduisant est :",options:["Autorisé à l'arrêt au feu rouge","Autorisé si vous roulez sous 30 km/h","Interdit — seul le kit mains-libres est toléré","Autorisé sur les routes peu fréquentées"],correct_answer:"Interdit — seul le kit mains-libres est toléré",explanation:'Le téléphone tenu en main est interdit en conduisant. L'attention requise pour conduire ne supporte pas de distraction.'},
    {id:'q26',number:26,category:'Sécurité',text:"Un siège enfant homologué est obligatoire pour :",options:["Les enfants de moins de 5 ans","Les enfants de moins de 10 ans ou mesurant moins de 1,35 m","Les enfants de moins de 3 ans uniquement","Les enfants de moins de 6 ans et moins de 15 kg"],correct_answer:"Les enfants de moins de 10 ans ou mesurant moins de 1,35 m",explanation:'Tout enfant de moins de 10 ans ou mesurant moins de 1,35 m doit être dans un dispositif de retenue homologué.'},
    {id:'q27',number:27,category:'Urgence',text:"Vos freins semblent défaillants en descente. La bonne réaction est :",options:["Couper le moteur immédiatement","Rétrograder, utiliser le frein à main progressivement, chercher un obstacle naturel","Accélérer pour passer le danger plus vite","Ouvrir la portière pour ralentir par friction"],correct_answer:"Rétrograder, utiliser le frein à main progressivement, chercher un obstacle naturel",explanation:'Freinage moteur + frein à main progressif (sans bloquer) + sortie contrôlée sont les bons réflexes face à une défaillance de freins.'},
    {id:'q28',number:28,category:'Urgence',text:"Votre voiture prend feu. La séquence correcte est :",options:["Appeler les pompiers depuis le véhicule puis sortir","S'arrêter, couper le moteur, sortir, s'éloigner, appeler les secours","Tenter d'éteindre avec l'eau du radiateur","Continuer à rouler vers un poste de secours"],correct_answer:"S'arrêter, couper le moteur, sortir, s'éloigner, appeler les secours",explanation:'Le risque d'explosion impose une évacuation immédiate. Éloignez-vous d'au moins 50 mètres avant d'appeler.'},
    {id:'q29',number:29,category:'Urgence',text:"En cas d'aquaplaning, vous devez :",options:["Freiner fort pour regagner l'adhérence","Tourner le volant en sens opposé au glissement","Lâcher l'accélérateur doucement et tenir le volant sans brusquerie","Changer de voie rapidement"],correct_answer:"Lâcher l'accélérateur doucement et tenir le volant sans brusquerie",explanation:'Tout geste brusque aggraverait la perte de contrôle. Relâchez doucement l'accélérateur et laissez les pneus reprendre contact.'},
    {id:'q30',number:30,category:'Urgence',text:"Sur une chaussée verglacée, la distance de freinage est :",options:["Identique à la route sèche","1,5 fois plus longue","5 à 10 fois plus longue","2 fois plus longue exactement"],correct_answer:"5 à 10 fois plus longue",explanation:'Sur verglas, la distance de freinage peut être multipliée par 5 à 10. Adaptez impérativement votre vitesse et vos distances.'},
    {id:'q31',number:31,category:'Alcool/Drogues',text:"Le taux d'alcoolémie maximal légal pour conduire en Guinée est :",options:["0,0 g/L","0,3 g/L de sang","0,5 g/L de sang","0,8 g/L de sang"],correct_answer:"0,5 g/L de sang",explanation:'La limite légale guinéenne est de 0,5 g/L de sang (0,25 mg/L d'air expiré), conforme aux normes CEDEAO.'},
    {id:'q32',number:32,category:'Alcool/Drogues',text:"La consommation de cannabis avant de conduire :",options:["N'a aucun effet sur la conduite","Perturbe réflexes, coordination et perception du temps — elle est interdite","Améliore la concentration","Est tolérée plusieurs heures après la consommation"],correct_answer:"Perturbe réflexes, coordination et perception du temps — elle est interdite",explanation:'Le cannabis altère significativement les capacités de conduite et reste détectable plusieurs heures après consommation.'},
    {id:'q33',number:33,category:'Alcool/Drogues',text:"Les médicaments peuvent-ils affecter la conduite ?",options:["Non, ils sont inoffensifs en doses normales","Oui — somnolence, réflexes diminués, troubles de vision ; lisez la notice","Seulement les médicaments à base de codéine","Seulement à forte dose"],correct_answer:"Oui — somnolence, réflexes diminués, troubles de vision ; lisez la notice",explanation:'Antihistaminiques, anxiolytiques, antidouleurs… nombreux médicaments altèrent la vigilance. Vérifiez toujours la notice.'},
    {id:'q34',number:34,category:'Premiers secours',text:"Vous arrivez sur un accident. Votre première action est :",options:["Prendre des photos de la scène","Protéger, Alerter, Secourir (PAS) — sécuriser la zone, appeler, aider","Déplacer immédiatement tous les blessés","Chercher les responsables"],correct_answer:"Protéger, Alerter, Secourir (PAS) — sécuriser la zone, appeler, aider",explanation:'La règle PAS : 1) Protéger (éviter sur-accident) 2) Alerter (secours) 3) Secourir (sans aggraver les blessures).'},
    {id:'q35',number:35,category:'Premiers secours',text:"Une victime est inconsciente mais respire. Que faites-vous ?",options:["La laisser sur le dos","La mettre en Position Latérale de Sécurité (PLS)","Lui donner de l'eau","La faire marcher pour la réveiller"],correct_answer:"La mettre en Position Latérale de Sécurité (PLS)",explanation:'La PLS maintient les voies respiratoires libres et prévient l'étouffement chez une victime inconsciente qui respire.'},
    {id:'q36',number:36,category:'Premiers secours',text:"Pour réduire la pollution, le conducteur doit :",options:["Garder le moteur au ralenti lors des arrêts","Couper le moteur pour les arrêts > 30 secondes et entretenir régulièrement son véhicule","Utiliser du carburant non filtré","Rouler vite pour consommer moins"],correct_answer:"Couper le moteur pour les arrêts > 30 secondes et entretenir régulièrement son véhicule",explanation:'Couper le moteur à l'arrêt réduit les émissions et la consommation. Un véhicule bien entretenu pollue moins.'},
    {id:'q37',number:37,category:'Signalisation',text:"Un feu vert pour les piétons signifie pour le conducteur :",options:["Il peut passer si aucun piéton n'est visible","Priorité absolue aux piétons — le conducteur doit s'arrêter","Il peut klaxonner et passer","Ce feu ne le concerne pas"],correct_answer:"Priorité absolue aux piétons — le conducteur doit s'arrêter",explanation:'Feu vert piéton = le conducteur DOIT s'arrêter et laisser traverser les piétons.'},
    {id:'q38',number:38,category:'Sécurité',text:"Vous êtes somnolent sur la route. Que faites-vous ?",options:["Ouvrez la fenêtre et maintenez votre vitesse","Boire un café et conduire encore 2h","Vous arrêter dès que possible et vous reposer","Mettre de la musique forte"],correct_answer:"Vous arrêter dès que possible et vous reposer",explanation:'La somnolence est aussi dangereuse que l'alcool. Seul le repos élimine le risque — aucune astuce ne compense.'},
    {id:'q39',number:39,category:'Priorités',text:"Vous tournez à gauche à un carrefour. Un piéton traverse en face. Vous devez :",options:["Passer rapidement avant le piéton","Céder le passage au piéton","Klaxonner pour qu'il accélère","Continuer si votre feu est vert"],correct_answer:"Céder le passage au piéton",explanation:'Tout véhicule tournant doit céder le passage aux piétons qui traversent la voie dans laquelle il s'engage.'},
    {id:'q40',number:40,category:'Dépassement',text:"Le dépassement par la droite est :",options:["Toujours interdit","Autorisé sur les routes à 3 voies","Interdit sauf en cas de file de gauche ralentissant ou lorsqu'un conducteur tourne à gauche","Autorisé si vous roulez vite"],correct_answer:"Interdit sauf en cas de file de gauche ralentissant ou lorsqu'un conducteur tourne à gauche",explanation:'Le dépassement par la droite est généralement interdit. Les exceptions sont strictement encadrées.'},
  ];
}

// ── Timer ────────────────────────────────────────────────────────────────

function Timer({ remainingSeconds, onExpire }: { remainingSeconds: number; onExpire: () => void }) {
  const [secs, setSecs] = useState(remainingSeconds);
  const expired = useRef(false);

  useEffect(() => {
    setSecs(remainingSeconds);
  }, [remainingSeconds]);

  useEffect(() => {
    if (secs <= 0 && !expired.current) {
      expired.current = true;
      onExpire();
      return;
    }
    const t = setTimeout(() => setSecs((s) => Math.max(0, s - 1)), 1000);
    return () => clearTimeout(t);
  }, [secs, onExpire]);

  const mins = Math.floor(secs / 60);
  const sec = secs % 60;
  const pct = remainingSeconds > 0 ? (secs / remainingSeconds) * 100 : 0;
  const urgent = secs <= 300; // < 5 min
  const critical = secs <= 60; // < 1 min

  return (
    <div className={`exam-timer ${urgent ? 'urgent' : ''} ${critical ? 'critical' : ''}`}>
      <div className="exam-timer-ring" style={{ '--pct': `${pct}%` } as React.CSSProperties}>
        <span className="exam-timer-value">
          {String(mins).padStart(2, '0')}:{String(sec).padStart(2, '0')}
        </span>
      </div>
      <p className="exam-timer-label">{critical ? '⚠️ Temps presque écoulé !' : urgent ? '⏳ Moins de 5 minutes' : 'Temps restant'}</p>
    </div>
  );
}

// ── Grille de navigation ──────────────────────────────────────────────────

function QuestionGrid({
  total,
  current,
  answers,
  onSelect,
}: {
  total: number;
  current: number;
  answers: Record<number, string>;
  onSelect: (i: number) => void;
}) {
  return (
    <div className="exam-question-grid">
      {Array.from({ length: total }, (_, i) => (
        <button
          key={i}
          type="button"
          className={[
            'exam-grid-cell',
            i === current ? 'active' : '',
            answers[i] !== undefined ? 'answered' : '',
          ].filter(Boolean).join(' ')}
          onClick={() => onSelect(i)}
          aria-label={`Question ${i + 1}${answers[i] !== undefined ? ' — répondue' : ''}`}
        >
          {i + 1}
        </button>
      ))}
    </div>
  );
}

// ── Rendu media ───────────────────────────────────────────────────────────

function QuestionMedia({ q }: { q: ExamQuestion }) {
  if (!q.media_url) return null;

  if (q.media_type === 'svg') {
    // Panneaux
    if (['stop','give_way','speed_50','no_entry','roundabout','mandatory','priority'].includes(q.media_url)) {
      return (
        <figure className="question-media-figure">
          <div className="question-media-sign">
            <SignSvg type={q.media_url} />
          </div>
          {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
        </figure>
      );
    }
    // Intersections
    if (q.media_url.startsWith('intersection_')) {
      return (
        <figure className="question-media-figure">
          <div className="question-media-scene">
            <IntersectionSvg type={q.media_url.replace('intersection_', '')} />
          </div>
          {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
        </figure>
      );
    }
    // Situations
    if (q.media_url.startsWith('situation_')) {
      return (
        <figure className="question-media-figure">
          <div className="question-media-scene">
            <SituationSvg type={q.media_url.replace('situation_', '')} />
          </div>
          {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
        </figure>
      );
    }
  }

  if (q.media_type === 'image' && q.media_url) {
    return (
      <figure className="question-media-figure">
        <img src={q.media_url} alt={q.media_alt ?? ''} className="question-media-img" />
        {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
      </figure>
    );
  }

  if (q.media_type === 'video' && q.media_url) {
    return (
      <figure className="question-media-figure">
        <video src={q.media_url} controls preload="metadata" className="question-media-video"
          aria-label={q.media_alt ?? 'Vidéo illustrative'} />
        {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
      </figure>
    );
  }

  return null;
}

// ── Page de résultats ─────────────────────────────────────────────────────

function ResultsView({ result }: { result: ExamResult }) {
  const [filter, setFilter] = useState<'all' | 'wrong' | 'correct'>('all');
  const filtered = result.questions.filter((q) =>
    filter === 'all' ? true : filter === 'correct' ? q.is_correct : !q.is_correct
  );

  return (
    <div className="exam-results">
      <div className={`exam-verdict ${result.passed ? 'passed' : 'failed'}`}>
        <div className="exam-verdict-icon">{result.passed ? '🏆' : '📋'}</div>
        <h2>{result.passed ? 'Félicitations — Admis !' : 'Ajourné'}</h2>
        <p className="exam-verdict-score">{result.score} / {result.total}</p>
        <p className="exam-verdict-pct">{result.score_percent}% — Seuil : {result.threshold}/{result.total} (87,5 %)</p>
        <p className="exam-verdict-name">{result.candidate_name}</p>
      </div>

      <div className="exam-results-filters">
        {(['all','correct','wrong'] as const).map((f) => (
          <button key={f} type="button"
            className={`exam-filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}>
            {f === 'all' ? `Toutes (${result.questions.length})` :
             f === 'correct' ? `✅ Correctes (${result.questions.filter((q) => q.is_correct).length})` :
             `❌ Incorrectes (${result.questions.filter((q) => !q.is_correct).length})`}
          </button>
        ))}
      </div>

      <div className="exam-results-list">
        {filtered.map((q) => (
          <div key={q.question_id ?? q.id} className={`result-item ${q.is_correct ? 'correct' : 'wrong'}`}>
            <div className="result-item-header">
              <span className="result-num">Q{q.number}</span>
              <span className="result-cat">{q.category}</span>
              <span className="result-badge">{q.is_correct ? '✅' : '❌'}</span>
            </div>
            <p className="result-question">{q.text}</p>
            {q.given_answer && (
              <p className="result-given">Votre réponse : <strong>{q.given_answer}</strong></p>
            )}
            {!q.is_correct && q.correct_answer && (
              <p className="result-correct">Bonne réponse : <strong>{q.correct_answer}</strong></p>
            )}
            {q.explanation && (
              <p className="result-explanation">💡 {q.explanation}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Composant principal ───────────────────────────────────────────────────

const DEMO_ATTEMPT_KEY = 'coderoute-demo-attempt-id';
const EXAM_DURATION = 30 * 60; // 30 min en secondes

export function ExamPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const isAuthenticated = !isPresentationMode && currentUser !== null;

  const [phase, setPhase] = useState<'setup' | 'running' | 'expired' | 'reviewing' | 'results'>('setup');
  const [questions, setQuestions] = useState<ExamQuestion[]>(buildDemoQuestions());
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(EXAM_DURATION);
  const [bookingRef, setBookingRef] = useState('');
  const [stationCode, setStationCode] = useState('POSTE-01');
  const [statusMsg, setStatusMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExamResult | null>(null);

  const currentQ = questions[currentIdx];
  const answeredCount = Object.keys(answers).length;

  // Charger les questions de l'API si disponibles
  useEffect(() => {
    if (!isAuthenticated || !attemptId) return;
    fetchWithAuth(`${API}/api/v1/exams/${attemptId}/questions`)
      .then((r) => r.json())
      .then((qs: ExamQuestion[]) => {
        if (Array.isArray(qs) && qs.length > 0) {
          // Enrichir les questions sans media avec une illustration par défaut
          const enriched = qs.map((q) => enrichWithMedia(q));
          setQuestions(enriched);
        }
      })
      .catch(() => {/* Garder les questions démo */});
  }, [attemptId, isAuthenticated]);

  // Polling du statut timer
  useEffect(() => {
    if (phase !== 'running' || !attemptId || !isAuthenticated) return;
    const interval = setInterval(() => {
      fetchWithAuth(`${API}/api/v1/exams/${attemptId}/status`)
        .then((r) => r.json())
        .then((s: ExamStatus) => {
          setRemainingSeconds(s.remaining_seconds);
          if (s.expired || s.status === 'expired') {
            setPhase('expired');
          }
        })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [phase, attemptId, isAuthenticated]);

  const handleTimerExpire = useCallback(() => {
    if (phase === 'running') setPhase('expired');
  }, [phase]);

  async function handleStart() {
    if (!isAuthenticated) {
      // Mode démo
      setAttemptId(`DEMO-${Date.now()}`);
      setPhase('running');
      setRemainingSeconds(EXAM_DURATION);
      setStatusMsg('Mode démonstration — examen simulé (30 min)');
      return;
    }
    if (!bookingRef.trim()) {
      setStatusMsg('Veuillez saisir une référence de réservation.');
      return;
    }
    setLoading(true);
    setStatusMsg('');
    try {
      const r = await fetchWithAuth(`${API}/api/v1/exams/start-from-booking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          booking_reference: bookingRef.trim(),
          device_key: stationCode.trim(),
          device_label: stationCode.trim(),
        }),
      });
      if (!r.ok) {
        const err = await r.json();
        setStatusMsg(err.detail ?? 'Impossible de démarrer l\'examen.');
        return;
      }
      const attempt = await r.json();
      setAttemptId(attempt.id);
      sessionStorage.setItem(DEMO_ATTEMPT_KEY, attempt.id);
      const statusR = await fetchWithAuth(`${API}/api/v1/exams/${attempt.id}/status`);
      const status: ExamStatus = await statusR.json();
      setRemainingSeconds(status.remaining_seconds);
      setPhase('running');
      setStatusMsg('');
    } catch {
      setStatusMsg('Erreur de connexion au serveur.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    if (phase === 'running' && answeredCount < questions.length) {
      setPhase('reviewing');
      return;
    }
    await doSubmit();
  }

  async function doSubmit() {
    const payload: Record<string, string> = {};
    questions.forEach((q, i) => {
      if (answers[i] !== undefined) payload[q.id] = answers[i];
    });

    if (!isAuthenticated || !attemptId || attemptId.startsWith('DEMO-')) {
      // Résultats démo
      const score = Object.values(payload).filter((_, i) => payload[questions[i]?.id] === questions[i]?.correct_answer).length;
      const demoResult: ExamResult = {
        attempt_id: attemptId ?? 'DEMO',
        candidate_name: currentUser?.full_name ?? 'Candidat',
        score,
        total: questions.length,
        score_percent: Math.round((score / questions.length) * 100 * 10) / 10,
        passed: score >= 35,
        threshold: 35,
        submitted_at: new Date().toISOString(),
        questions: questions.map((q, i) => ({
          ...q,
          given_answer: answers[i],
          is_correct: answers[i] === q.correct_answer,
        })),
      };
      setResult(demoResult);
      setPhase('results');
      return;
    }

    setLoading(true);
    try {
      const r = await fetchWithAuth(`${API}/api/v1/exams/${attemptId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: payload }),
      });
      if (!r.ok) {
        const err = await r.json();
        setStatusMsg(err.detail ?? 'Erreur lors de la soumission.');
        return;
      }
      // Charger les résultats détaillés
      const resR = await fetchWithAuth(`${API}/api/v1/exams/${attemptId}/results`);
      const res: ExamResult = await resR.json();
      setResult(res);
      setPhase('results');
    } catch {
      setStatusMsg('Erreur lors de la soumission.');
    } finally {
      setLoading(false);
    }
  }

  function selectAnswer(option: string) {
    setAnswers((prev) => ({ ...prev, [currentIdx]: option }));
  }

  // ── Rendu phase setup ────────────────────────────────────────────────

  if (phase === 'setup') {
    return (
      <section className="screen exam-screen">
        <div className="exam-setup-card">
          <div className="exam-setup-header">
            <span className="eyebrow">Examen officiel</span>
            <h2>Code de la route — Catégorie B</h2>
            <p>40 questions · 30 minutes · Seuil d'admission : 35/40 (87,5 %)</p>
          </div>
          <div className="exam-setup-rules">
            <div className="rule-item"><span>📋</span><span>40 questions illustrées</span></div>
            <div className="rule-item"><span>⏱️</span><span>30 minutes chronométrées</span></div>
            <div className="rule-item"><span>✅</span><span>35 bonnes réponses requises</span></div>
            <div className="rule-item"><span>🔒</span><span>Navigation libre entre questions</span></div>
            <div className="rule-item"><span>🎯</span><span>Résultats détaillés à la fin</span></div>
          </div>

          {isAuthenticated ? (
            <div className="exam-setup-fields">
              <label>
                Référence de réservation
                <input value={bookingRef} onChange={(e) => setBookingRef(e.target.value)}
                  placeholder="GN-BOOK-..." />
              </label>
              <label>
                Code du poste
                <input value={stationCode} onChange={(e) => setStationCode(e.target.value)}
                  placeholder="POSTE-01" />
              </label>
            </div>
          ) : (
            <p className="exam-demo-notice">
              🎓 Mode démonstration — 40 questions illustrées disponibles sans connexion
            </p>
          )}

          {statusMsg && <p className="form-error">{statusMsg}</p>}

          <button className="exam-start-btn" onClick={handleStart} disabled={loading}>
            {loading ? 'Démarrage...' : isAuthenticated ? '🚀 Démarrer l\'examen officiel' : '🎓 Commencer la démonstration'}
          </button>
        </div>
      </section>
    );
  }

  // ── Rendu phase reviewing (avant soumission) ──────────────────────────

  if (phase === 'reviewing') {
    const unanswered = questions.filter((_, i) => answers[i] === undefined);
    return (
      <section className="screen exam-screen">
        <div className="exam-review-card">
          <h2>Vérification avant soumission</h2>
          <p>Vous avez répondu à <strong>{answeredCount}</strong> question(s) sur {questions.length}.</p>
          {unanswered.length > 0 && (
            <div className="exam-unanswered-list">
              <p className="warning-text">⚠️ Questions sans réponse :</p>
              {unanswered.map((q) => (
                <button key={q.id} type="button" className="unanswered-btn"
                  onClick={() => { setCurrentIdx(q.number - 1); setPhase('running'); }}>
                  Question {q.number} — {q.category}
                </button>
              ))}
            </div>
          )}
          <div className="review-actions">
            <button className="secondary-button" onClick={() => setPhase('running')}>↩ Revenir à l'examen</button>
            <button className="exam-submit-final" onClick={doSubmit} disabled={loading}>
              {loading ? 'Soumission...' : '✅ Soumettre définitivement'}
            </button>
          </div>
        </div>
      </section>
    );
  }

  // ── Rendu phase expired ───────────────────────────────────────────────

  if (phase === 'expired') {
    return (
      <section className="screen exam-screen">
        <div className="exam-expired-card">
          <p className="exam-expired-icon">⏰</p>
          <h2>Temps écoulé</h2>
          <p>Le temps de 30 minutes est écoulé. Vos réponses vont être soumises automatiquement.</p>
          <button onClick={doSubmit} disabled={loading}>
            {loading ? 'Soumission...' : 'Voir mes résultats'}
          </button>
        </div>
      </section>
    );
  }

  // ── Rendu phase results ───────────────────────────────────────────────

  if (phase === 'results' && result) {
    return (
      <section className="screen exam-screen">
        <ResultsView result={result} />
      </section>
    );
  }

  // ── Rendu phase running ───────────────────────────────────────────────

  if (!currentQ) return null;

  return (
    <section className="screen exam-screen exam-screen--running">
      {/* Sidebar gauche : timer + grille */}
      <aside className="exam-sidebar">
        <Timer remainingSeconds={remainingSeconds} onExpire={handleTimerExpire} />

        <div className="exam-sidebar-info">
          <p><strong>{answeredCount}</strong> / {questions.length} répondues</p>
          <p>Seuil : 35/40</p>
        </div>

        <QuestionGrid
          total={questions.length}
          current={currentIdx}
          answers={answers}
          onSelect={setCurrentIdx}
        />

        <button className="exam-submit-btn" onClick={handleSubmit} disabled={loading}>
          {loading ? 'En cours...' : answeredCount < questions.length
            ? `Vérifier (${questions.length - answeredCount} sans réponse)`
            : '✅ Soumettre l\'examen'}
        </button>

        {statusMsg && <p className="form-error" style={{ fontSize: 12 }}>{statusMsg}</p>}
      </aside>

      {/* Zone principale : question */}
      <main className="exam-main">
        <div className="exam-main-header">
          <span className="exam-q-cat">{currentQ.category}</span>
          <span className="exam-q-num">Question {currentIdx + 1} / {questions.length}</span>
        </div>

        {/* Barre de progression */}
        <div className="exam-progress-bar">
          <div className="exam-progress-fill" style={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }} />
        </div>

        {/* Media illustratif */}
        <QuestionMedia q={currentQ} />

        {/* Texte de la question */}
        <p className="exam-question-text">{currentQ.text}</p>

        {/* Options */}
        <div className="exam-options">
          {currentQ.options.map((opt, oi) => (
            <button
              key={oi}
              type="button"
              className={`exam-option ${answers[currentIdx] === opt ? 'selected' : ''}`}
              onClick={() => selectAnswer(opt)}
            >
              <span className="exam-option-letter">{String.fromCharCode(65 + oi)}</span>
              <span className="exam-option-text">{opt}</span>
              {answers[currentIdx] === opt && <span className="exam-option-check">✓</span>}
            </button>
          ))}
        </div>

        {/* Navigation */}
        <div className="exam-nav">
          <button
            className="secondary-button"
            disabled={currentIdx === 0}
            onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
          >
            ← Précédente
          </button>
          <span className="exam-nav-skip">
            {answers[currentIdx] === undefined ? (
              <button className="exam-skip-btn"
                onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}>
                Passer →
              </button>
            ) : null}
          </span>
          <button
            disabled={currentIdx === questions.length - 1}
            onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}
          >
            Suivante →
          </button>
        </div>
      </main>
    </section>
  );
}

// ── Enrichissement automatique des questions API sans media ────────────────

function enrichWithMedia(q: ExamQuestion): ExamQuestion {
  if (q.media_url) return q;
  const cat = q.category.toLowerCase();
  if (cat.includes('signal')) return { ...q, media_type: 'svg', media_url: 'priority', media_alt: 'Illustration signalisation' };
  if (cat.includes('priorit')) return { ...q, media_type: 'svg', media_url: 'intersection_priority_right', media_alt: 'Situation de priorité' };
  if (cat.includes('girat') || cat.includes('rondpoint')) return { ...q, media_type: 'svg', media_url: 'intersection_roundabout', media_alt: 'Giratoire' };
  if (cat.includes('vitesse') || cat.includes('distance')) return { ...q, media_type: 'svg', media_url: 'situation_safe_distance', media_alt: 'Distance de sécurité' };
  if (cat.includes('dépasse') || cat.includes('manoeuv')) return { ...q, media_type: 'svg', media_url: 'situation_overtake_forbidden', media_alt: 'Situation de dépassement' };
  if (cat.includes('urgence') || cat.includes('secours')) return { ...q, media_type: 'svg', media_url: 'situation_emergency_vehicle', media_alt: 'Véhicule d\'urgence' };
  return q;
}
