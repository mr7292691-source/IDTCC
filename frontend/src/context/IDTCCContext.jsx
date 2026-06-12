import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { LOCATION_CATALOGUE, BASE_RESOURCES } from '../data/locationCatalogue.js';
import { generateTwins } from '../data/generateTwins.js';
import {
  runSimulation, assignSafeSpaces, buildSafeSpaceReport, makeCycloneParams,
} from '../data/cycloneEngine.js';
import {
  agentWeather, agentRiskExposure, agentClaimsForecast,
  agentFraudDetection, agentReserveCalculation, agentResourcePlanning,
  agentCustomerAlerts, buildJudgeResults, buildForecast,
} from '../data/agents.js';

const IDTCCContext = createContext(null);

export function IDTCCProvider({ children }) {
  const [locationKey, setLocationKey] = useState('CHN');
  const [isLoading, setIsLoading]     = useState(true);
  const [loadingMsg, setLoadingMsg]   = useState('Initialising digital twin portfolio...');
  const [data, setData]               = useState(null);
  const [activeView, setActiveView]   = useState('command');
  const generatedRef = useRef({});

  const computeAll = (locKey) => {
    const loc = LOCATION_CATALOGUE[locKey];

    setLoadingMsg('Generating 50,000 property twins...');
    const baseTwins = generateTwins(loc, 50000);

    setLoadingMsg('Running cyclone simulation engine...');
    const cycloneParams = makeCycloneParams(loc);
    const simTwins = runSimulation(baseTwins, cycloneParams);

    setLoadingMsg('Assigning safe spaces & building social vulnerability layer...');
    const safeSpaces = loc.safeSpaces.map(ss => ({
      ...ss,
      resources: { ...BASE_RESOURCES },
      has_medical_team: true,
      elevation_m: 8.0,
    }));
    const twins = assignSafeSpaces(simTwins, safeSpaces);

    setLoadingMsg('Running AI agents...');
    const weatherOut  = agentWeather(cycloneParams);
    const riskOut     = agentRiskExposure(twins, cycloneParams);
    const claimsOut   = agentClaimsForecast(twins);
    const fraudOut    = agentFraudDetection(twins);
    const reserveOut  = agentReserveCalculation(twins, claimsOut);
    const resourceOut = agentResourcePlanning(twins);
    const alertsOut   = agentCustomerAlerts(twins, cycloneParams.name);

    setLoadingMsg('Running LLM-as-Judge evaluation...');
    const ssReport    = buildSafeSpaceReport(twins, safeSpaces, BASE_RESOURCES);
    const judgeOut    = buildJudgeResults(weatherOut, claimsOut, ssReport, reserveOut);
    const forecast    = buildForecast(cycloneParams, weatherOut, riskOut, claimsOut, fraudOut, reserveOut, resourceOut);

    return {
      loc, baseTwins, twins, cycloneParams, safeSpaces, ssReport,
      weatherOut, riskOut, claimsOut, fraudOut, reserveOut,
      resourceOut, alertsOut, judgeOut, forecast,
    };
  };

  useEffect(() => {
    setIsLoading(true);

    // Small delay to let loading screen render first
    const timer = setTimeout(() => {
      try {
        const result = computeAll(locationKey);
        generatedRef.current[locationKey] = result;
        setData(result);
      } catch (err) {
        console.error('IDTCC init error:', err);
      }
      setIsLoading(false);
    }, 50);

    return () => clearTimeout(timer);
  }, [locationKey]);

  const changeLocation = (key) => {
    if (key === locationKey) return;
    setLocationKey(key);
  };

  const value = {
    locationKey, changeLocation,
    isLoading, loadingMsg,
    activeView, setActiveView,
    ...(data || {}),
  };

  return <IDTCCContext.Provider value={value}>{children}</IDTCCContext.Provider>;
}

export function useIDTCC() {
  const ctx = useContext(IDTCCContext);
  if (!ctx) throw new Error('useIDTCC must be used inside IDTCCProvider');
  return ctx;
}
