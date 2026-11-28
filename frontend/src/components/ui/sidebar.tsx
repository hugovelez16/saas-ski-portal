"use client";

import React, { useState, useEffect, createContext, useContext } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    FileText,
    Calendar,
    Settings,
    LogOut,
    ChevronLeft,
    ChevronRight,
    ChevronDown,
    Menu,
    X,
    PanelLeftClose,
    PanelLeftOpen,
    Ghost,
    Building2,
    Scale
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { getMyCompanies } from "@/lib/api/companies";
import { ScopeSelectionDialog } from "@/components/auth/scope-selection-dialog";


// Sidebar Context for global state if needed
const SidebarContext = createContext<{ expanded: boolean; setExpanded: (v: boolean) => void }>({
    expanded: true,
    setExpanded: () => { },
});

export function SidebarProvider({ children }: { children: React.ReactNode }) {
    const [expanded, setExpanded] = useState(true);

    return (
        <SidebarContext.Provider value={{ expanded, setExpanded }}>
            {children}
        </SidebarContext.Provider>
    );
}

export type NavItem = {
    href: string;
    label: string;
    icon: any;
};

export type NavGroup = {
    label?: string;
    items: NavItem[];
};

export function Sidebar({ navGroups }: { navGroups: NavGroup[] }) {
    const { expanded, setExpanded } = useContext(SidebarContext);
    const { user, logout, stopImpersonation } = useAuth();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const [isMobile, setIsMobile] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [isScopeDialogOpen, setIsScopeDialogOpen] = useState(false);

    // Fetch companies to show active company name
    const { data: companies = [] } = useQuery({
        queryKey: ["myCompanies"],
        queryFn: getMyCompanies,
        enabled: !!user,
    });

    const activeCompany = companies.find(c => c.id === user?.activeCompanyId);

    // State to track expanded groups. key = group index
    // Default open all
    const [openGroups, setOpenGroups] = useState<Record<number, boolean>>({});

    useEffect(() => {
        // Initialize all groups as open
        const initial: Record<number, boolean> = {};
        navGroups.forEach((_, i) => { initial[i] = true; });
        setOpenGroups(initial);
    }, [navGroups.length]);

    const toggleGroup = (index: number) => {
        setOpenGroups(prev => ({ ...prev, [index]: !prev[index] }));
    };

    // Detect mobile screen
    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 768);
        checkMobile();
        window.addEventListener("resize", checkMobile);
        return () => window.removeEventListener("resize", checkMobile);
    }, []);

    // Helper to render items
    const renderItems = (items: NavItem[]) => (
        items.map((item) => {
            const Icon = item.icon;

            // Active State Logic
            const [itemPath, itemQuery] = item.href.split('?');
            let isActive = pathname === itemPath || pathname.startsWith(`${itemPath}/`);

            if (isActive && itemQuery) {
                const itemParams = new URLSearchParams(itemQuery);
                itemParams.forEach((val, key) => {
                    const currentVal = searchParams.get(key);
                    if (currentVal !== val) {
                        isActive = false;
                    }
                });
            }

            return (
                <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                        "flex items-center space-x-3 pl-6 pr-3 py-2 rounded-md transition-colors whitespace-nowrap mb-1",
                        isActive
                            ? "bg-primary text-primary-foreground shadow-sm font-medium"
                            : "text-slate-400 hover:bg-slate-800 hover:text-white hover:pl-4 transition-all",
                        !expanded && "justify-center px-0 hover:pl-0"
                    )}
                    title={!expanded ? item.label : undefined}
                >
                    <Icon size={20} className="flex-shrink-0" />
                    {expanded && (
                        <motion.span
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.1 }}
                        >
                            {item.label}
                        </motion.span>
                    )}
                </Link>
            );
        })
    );

    // Desktop Sidebar
    return (
        <>
            {/* Mobile Header - Sticky */}
            <div className="md:hidden sticky top-0 z-40 flex items-center justify-between p-4 bg-slate-900 text-white shadow-md">
                <Button variant="ghost" size="icon" onClick={() => setMobileOpen(true)} className="text-white hover:bg-slate-800">
                    <Menu size={24} />
                </Button>
                <span className="font-bold">Ski Vesotel (Jornadas)</span>
            </div>

            {/* Mobile Sidebar (Drawer) */}
            <AnimatePresence>
                {mobileOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 0.5 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setMobileOpen(false)}
                            className="fixed inset-0 bg-black z-[60]"
                        />
                        <motion.div
                            initial={{ x: "-100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "-100%" }}
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            className="fixed inset-y-0 left-0 w-64 bg-slate-900 text-white z-[60] shadow-xl flex flex-col"
                        >
                            <div className="p-4 flex items-center justify-between border-b border-slate-800">
                                <div>
                                    <h2 className="font-bold">Menu</h2>
                                    <p className="text-xs text-slate-400">Hola, {user?.firstName}</p>
                                </div>
                                <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} className="text-white">
                                    <X size={20} />
                                </Button>
                            </div>

                            <nav className="flex-1 p-4 space-y-4 overflow-y-auto">
                                {navGroups.map((group, i) => (
                                    <div key={i}>
                                        {group.label && (
                                            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 px-3">
                                                {group.label}
                                            </div>
                                        )}
                                        {renderItems(group.items)}
                                        {i < navGroups.length - 1 && <div className="h-px bg-slate-800 my-4" />}
                                    </div>
                                ))}
                            </nav>



                            <div className="p-4 border-t border-slate-800">
                                <Link href="/profile" onClick={() => setMobileOpen(false)} className="flex items-center space-x-3 mb-4 px-3 py-2 rounded-md hover:bg-slate-800 transition-colors">
                                    <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center font-bold flex-shrink-0">
                                        {user?.firstName?.[0]}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-sm font-medium truncate">{user?.firstName}</p>
                                        <p className="text-xs text-slate-400 truncate">{user?.email}</p>
                                    </div>
                                </Link>

                                {user?.isImpersonated && (
                                    <button 
                                        onClick={stopImpersonation} 
                                        className="flex items-center space-x-3 text-amber-500 w-full px-3 py-2 hover:bg-amber-500/10 rounded-md transition-colors mb-2 bg-amber-500/5"
                                    >
                                        <Ghost size={20} />
                                        <span>Finalizar Simulación</span>
                                    </button>
                                )}

                                <button 
                                    onClick={() => { setIsScopeDialogOpen(true); setMobileOpen(false); }}
                                    className="flex items-center space-x-3 text-indigo-400 w-full px-3 py-2 hover:bg-white/5 rounded-md transition-colors mb-2"
                                >
                                    <Building2 size={20} />
                                    <div className="flex flex-col items-start translate-y-[1px] min-w-0 flex-1">
                                        <span className="text-sm font-medium">Cambiar Contexto</span>
                                        <span className="text-[10px] opacity-70 uppercase tracking-tighter truncate w-full text-left">
                                            {activeCompany ? `${activeCompany.name} • ` : ''}
                                            {user?.isPlatformAdmin && !user?.activeRole ? 'Administrador' : (user?.activeRole === 'manager' ? 'Manager' : 'Trabajador')}
                                        </span>
                                    </div>
                                </button>

                                <Link
                                    href="/aviso-legal"
                                    onClick={() => setMobileOpen(false)}
                                    className="flex items-center space-x-3 text-xs text-slate-400 hover:text-slate-200 w-full px-3 py-2 hover:bg-slate-800/50 rounded-md transition-colors mb-1"
                                >
                                    <Scale size={18} className="flex-shrink-0" />
                                    <span>Información legal</span>
                                </Link>

                                <button onClick={logout} className="flex items-center space-x-3 text-red-400 w-full px-3 py-2 hover:bg-slate-800/50 rounded-md transition-colors">
                                    <LogOut size={20} />
                                    <span>Log Out (Salir)</span>
                                </button>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* Desktop Sidebar */}
            <motion.aside
                animate={{ width: expanded ? 256 : 80 }}
                className="hidden md:flex flex-col bg-slate-900 text-slate-50 flex-shrink-0 relative h-screen sticky top-0"
            >
                <div className="p-4 border-b border-slate-800 h-16 flex items-center justify-between overflow-hidden whitespace-nowrap">
                    {expanded ? (
                        <div className="min-w-0">
                            <h1 className="font-bold text-lg truncate">Vesotel</h1>
                            <p className="text-xs text-slate-400 truncate">Jornadas</p>
                        </div>
                    ) : (
                        <span className="font-bold text-xl mx-auto">V</span>
                    )}

                    <button
                        onClick={() => setExpanded(!expanded)}
                        className={cn(
                            "text-slate-400 hover:text-white transition-colors",
                            !expanded && "hidden"
                        )}
                    >
                        {expanded && <PanelLeftClose size={18} />}
                    </button>
                </div>

                {!expanded && (
                    <button
                        onClick={() => setExpanded(true)}
                        className="w-full flex justify-center py-2 text-slate-400 hover:text-white"
                    >
                        <PanelLeftOpen size={20} />
                    </button>
                )}

                {/* Company Switcher Area (Removed) */}

                <nav className="flex-1 p-4 overflow-x-hidden overflow-y-auto custom-scrollbar">
                    {navGroups.map((group, i) => (
                        <div key={i} className="mb-2">
                            {/* Divider if not first and not collapsed mode (or divider in collapsed too?) */}
                            {i > 0 && (
                                <div className={cn("h-px bg-slate-800 my-2", !expanded && "mx-2")} />
                            )}

                            {/* Group Header (Expanded Only) */}
                            {expanded && group.label && (
                                <button
                                    onClick={() => toggleGroup(i)}
                                    className="flex items-center justify-between w-full text-sm font-bold text-slate-500 uppercase tracking-wider mb-2 px-3 hover:text-slate-300 transition-colors"
                                >
                                    <span>{group.label}</span>
                                    {openGroups[i] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                </button>
                            )}

                            {/* Items - Collapsible only if expanded mode */}
                            <AnimatePresence initial={false}>
                                {(expanded ? openGroups[i] !== false : true) && (
                                    <motion.div
                                        initial={expanded ? { height: 0, opacity: 0 } : undefined}
                                        animate={expanded ? { height: "auto", opacity: 1 } : undefined}
                                        exit={expanded ? { height: 0, opacity: 0 } : undefined}
                                        className="overflow-hidden"
                                    >
                                        {renderItems(group.items)}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    ))}


                </nav>

                <div className="p-4 mt-auto border-t border-slate-800 overflow-hidden whitespace-nowrap">
                    {/* Switch Scope Button */}
                    <button
                        onClick={() => setIsScopeDialogOpen(true)}
                        className={cn(
                            "flex items-center space-x-3 px-3 py-2 text-indigo-400 hover:text-indigo-300 w-full transition-colors mb-2 hover:bg-white/5 rounded-md group",
                            !expanded && "justify-center px-0 mx-auto w-[40px]"
                        )}
                        title="Cambiar Contexto"
                    >
                        <Building2 size={20} className="flex-shrink-0" />
                        {expanded && (
                            <div className="flex flex-col items-start min-w-0 flex-1">
                                <span className="text-sm font-medium">Cambiar Contexto</span>
                                <span className="text-[10px] opacity-50 uppercase font-bold tracking-tighter truncate w-full text-left">
                                    {activeCompany ? `${activeCompany.name} • ` : ''}
                                    {user?.isPlatformAdmin && !user?.activeRole ? 'Administrador' : (user?.activeRole === 'manager' ? 'Manager' : 'Trabajador')}
                                </span>
                            </div>
                        )}
                    </button>

                    {user?.isImpersonated && (
                        <button
                            onClick={stopImpersonation}
                            className={cn(
                                "flex items-center space-x-3 px-3 py-2 text-amber-500 hover:text-amber-600 w-full transition-colors whitespace-nowrap mb-2 bg-amber-500/10 rounded-md",
                                !expanded && "justify-center px-0 mx-auto w-[40px]"
                            )}
                            title="Finalizar Simulación"
                        >
                            <Ghost size={20} className="flex-shrink-0" />
                            {expanded && <span>Finalizar Simulación</span>}
                        </button>
                    )}

                    <Link href="/profile" className="flex items-center space-x-3 mb-2 px-3 hover:bg-slate-800 rounded-md py-2 transition-colors cursor-pointer block">
                        {!expanded ? (
                            <div className="w-8 h-8 rounded-full bg-slate-700 mx-auto flex items-center justify-center font-bold">
                                {user?.firstName?.[0]}
                            </div>
                        ) : (
                            <>
                                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center font-bold flex-shrink-0">
                                    {user?.firstName?.[0]}
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="text-sm font-medium truncate">{user?.firstName}</p>
                                    <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                                </div>
                            </>
                        )}
                    </Link>

                    <Link
                        href="/aviso-legal"
                        aria-label="Información legal"
                        title="Información legal"
                        className={cn(
                            "flex items-center space-x-3 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 w-full transition-colors whitespace-nowrap rounded-md hover:bg-slate-800/50 mb-1",
                            !expanded && "justify-center px-0"
                        )}
                    >
                        <Scale size={18} className="flex-shrink-0" />
                        {expanded && <span>Información legal</span>}
                    </Link>

                    <button
                        onClick={logout}
                        className={cn(
                            "flex items-center space-x-3 px-3 py-2 text-slate-400 hover:text-red-400 w-full transition-colors whitespace-nowrap",
                            !expanded && "justify-center px-0"
                        )}
                        title="Cerrar Sesión"
                    >
                        <LogOut size={20} className="flex-shrink-0" />
                        {expanded && <span>Log Out (Salir)</span>}
                    </button>
                </div>

                <ScopeSelectionDialog open={isScopeDialogOpen} onOpenChange={setIsScopeDialogOpen} />
            </motion.aside>
        </>
    );
}
