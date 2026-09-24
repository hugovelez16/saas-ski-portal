import { render, screen, fireEvent, renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EventCalendar } from "../event-calendar";
import { CalendarConfigProvider, useCalendarConfig } from "../use-calendar-config";
import { DayView } from "../day-view";
import { WeekView } from "../week-view";

// Mock para ResizeObserver que usa DndKit internamente
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock para localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    clear: vi.fn(() => {
      store = {};
    })
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

describe("useCalendarConfig", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("should initialize with default values (0 to 24)", () => {
    const { result } = renderHook(() => useCalendarConfig(), { wrapper: CalendarConfigProvider });
    expect(result.current.startHour).toBe(0);
    expect(result.current.endHour).toBe(24);
  });

  it("should load from localStorage if exists", () => {
    localStorageMock.setItem("calendar_hours_preference", JSON.stringify({ start: 8, end: 18 }));
    const { result } = renderHook(() => useCalendarConfig(), { wrapper: CalendarConfigProvider });
    expect(result.current.startHour).toBe(8);
    expect(result.current.endHour).toBe(18);
  });

  it("should save to localStorage when updated", () => {
    const { result } = renderHook(() => useCalendarConfig(), { wrapper: CalendarConfigProvider });
    
    act(() => {
      result.current.setStartHour(9);
    });
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "calendar_hours_preference", 
      JSON.stringify({ start: 9, end: 24 })
    );

    act(() => {
      result.current.setEndHour(17);
    });
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "calendar_hours_preference", 
      JSON.stringify({ start: 9, end: 17 })
    );
  });
});

describe("EventCalendar TimeRangeSelector", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("should render time selectors and change values", () => {
    render(<EventCalendar />);
    
    // Los combobox son los selects nativos. Debería haber dos: 'Desde:' y 'Hasta:'
    const selects = screen.getAllByRole("combobox");
    expect(selects).toHaveLength(2);
    const startSelect = selects[0] as HTMLSelectElement;
    const endSelect = selects[1] as HTMLSelectElement;

    expect(startSelect.value).toBe("0");
    expect(endSelect.value).toBe("24");

    fireEvent.change(startSelect, { target: { value: '8' } });
    expect(startSelect.value).toBe("8");

    fireEvent.change(endSelect, { target: { value: '18' } });
    expect(endSelect.value).toBe("18");
  });
});

describe("DayView / WeekView configuration", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("should limit hours rendered in DayView based on config", () => {
    localStorageMock.setItem("calendar_hours_preference", JSON.stringify({ start: 10, end: 14 }));
    
    render(
      <CalendarConfigProvider>
        <DayView currentDate={new Date("2024-01-01")} events={[]} onEventCreate={() => {}} onEventSelect={() => {}} />
      </CalendarConfigProvider>
    );

    // Se renderizan los textos de horas para index > 0. Si el inicio es 10, el index 0 es 10:00 (oculto).
    // 11:00, 12:00 y 13:00 deberían estar visibles, pero no 14:00 (endHour).
    expect(screen.queryByText("09:00")).toBeNull();
    expect(screen.getByText("11:00")).toBeInTheDocument();
    expect(screen.getByText("12:00")).toBeInTheDocument();
    expect(screen.getByText("13:00")).toBeInTheDocument();
    expect(screen.queryByText("14:00")).toBeNull();
  });

  it("should limit hours rendered in WeekView based on config", () => {
    localStorageMock.setItem("calendar_hours_preference", JSON.stringify({ start: 8, end: 12 }));
    
    render(
      <CalendarConfigProvider>
        <WeekView currentDate={new Date("2024-01-01")} events={[]} onEventCreate={() => {}} onEventSelect={() => {}} />
      </CalendarConfigProvider>
    );

    expect(screen.queryByText("07:00")).toBeNull();
    expect(screen.getByText("09:00")).toBeInTheDocument();
    expect(screen.getByText("10:00")).toBeInTheDocument();
    expect(screen.getByText("11:00")).toBeInTheDocument();
    expect(screen.queryByText("12:00")).toBeNull();
  });
});
