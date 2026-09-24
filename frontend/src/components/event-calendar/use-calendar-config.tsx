"use client";

import { createContext, useContext, useEffect, useState } from "react";

interface CalendarConfig {
  startHour: number;
  endHour: number;
  setStartHour: (hour: number) => void;
  setEndHour: (hour: number) => void;
}

const CalendarConfigContext = createContext<CalendarConfig | null>(null);

const STORAGE_KEY = "calendar_hours_preference";

export function CalendarConfigProvider({ children }: { children: React.ReactNode }) {
  const [startHour, setStartHour] = useState<number>(0);
  const [endHour, setEndHour] = useState<number>(24);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const { start, end } = JSON.parse(stored);
        if (typeof start === "number" && typeof end === "number" && start >= 0 && end <= 24 && start < end) {
          setStartHour(start);
          setEndHour(end);
        }
      }
    } catch (e) {
      console.error("Failed to parse calendar config", e);
    }
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ start: startHour, end: endHour }));
    }
  }, [startHour, endHour, isLoaded]);

  // Se renderiza siempre para evitar desajustes de hidratación (SSR)
  return (
    <CalendarConfigContext.Provider value={{ startHour, endHour, setStartHour, setEndHour }}>
      {children}
    </CalendarConfigContext.Provider>
  );
}

export function useCalendarConfig() {
  const context = useContext(CalendarConfigContext);
  if (!context) {
    throw new Error("useCalendarConfig must be used within a CalendarConfigProvider");
  }
  return context;
}
