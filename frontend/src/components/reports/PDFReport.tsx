/* eslint-disable jsx-a11y/alt-text */
"use client";

import React, { useMemo } from 'react';
import { Page, Text, View, Document, StyleSheet, Image, Font } from '@react-pdf/renderer';
import { format, parseISO, eachDayOfInterval } from 'date-fns';
import { WorkLog, Company } from '@/lib/types';
import { formatCurrency } from '@/lib/utils';

// Register standard fonts
Font.register({
    family: 'Helvetica',
    fonts: [
        { src: 'https://fonts.gstatic.com/s/helveticaneue/v70/1Ptsg8zYS_SKggPNyC0IT4ttDfA.ttf' },
        { src: 'https://fonts.gstatic.com/s/helveticaneue/v70/1Ptsg8zYS_SKggPNyC0IT4ttDfA.ttf', fontWeight: 'bold' } // Fallback to standard names if URL fails, but React-PDF has bold helpers
    ]
});

const styles = StyleSheet.create({
    page: {
        padding: 30,
        backgroundColor: '#ffffff',
        fontFamily: 'Helvetica',
        color: '#334155',
        fontSize: 10,
    },
    // Header
    headerContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#0f172a', // Slate-900
        padding: 20,
        margin: -30,
        marginBottom: 30,
    },
    headerLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 15,
    },
    logoBox: {
        width: 35,
        height: 35,
        backgroundColor: '#1e293b',
        borderRadius: 4,
        alignItems: 'center',
        justifyContent: 'center',
        border: '1pt solid #334155'
    },
    logoText: {
        color: 'white',
        fontSize: 16,
        fontWeight: 'bold',
    },
    appTitle: {
        fontSize: 16,
        color: 'white',
        fontWeight: 'bold',
        textTransform: 'uppercase',
    },
    appSubtitle: {
        fontSize: 9,
        color: '#94a3b8',
        textTransform: 'uppercase',
        marginTop: 2,
    },
    headerRight: {
        alignItems: 'flex-end',
    },
    reportTitle: {
        color: 'white',
        fontWeight: 'bold',
        fontSize: 12,
        marginBottom: 2,
    },
    generatedDate: {
        color: '#94a3b8',
        fontSize: 9,
        fontFamily: 'Helvetica',
    },

    // Summary Section
    sectionTitle: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#0f172a',
        borderLeftWidth: 4,
        borderLeftColor: '#0f172a',
        paddingLeft: 8,
        marginBottom: 15,
    },
    summaryGrid: {
        flexDirection: 'row',
        gap: 10,
        marginBottom: 20,
    },
    card: {
        flex: 1,
        backgroundColor: '#f8fafc',
        borderRadius: 6,
        padding: 12,
        borderWidth: 1,
        borderColor: '#e2e8f0',
    },
    cardTitle: {
        fontSize: 8,
        color: '#64748b',
        fontWeight: 'bold',
        textTransform: 'uppercase',
        marginBottom: 6,
    },
    cardValue: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#0f172a',
    },
    cardSubValue: {
        fontSize: 10,
        color: '#94a3b8',
        marginTop: 2,
        fontWeight: 'normal',
    },

    // Charts
    chartSection: {
        flexDirection: 'row',
        gap: 20,
        marginBottom: 30,
        height: 180,
    },
    chartContainer: {
        flex: 1,
        alignItems: 'center',
        backgroundColor: '#f8fafc',
        borderRadius: 6,
        padding: 10,
        borderWidth: 1,
        borderColor: '#e2e8f0',
    },
    chartTitle: {
        fontSize: 8,
        fontWeight: 'bold',
        color: '#64748b',
        textTransform: 'uppercase',
        marginBottom: 5,
    },
    chartImage: {
        width: '100%',
        height: 140,
        objectFit: 'contain',
    },

    // Monthly Groups
    monthContainer: {
        marginTop: 15,
        marginBottom: 5,
        breakInside: 'avoid',
    },
    monthHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 10,
    },
    monthTitle: {
        fontSize: 12,
        fontWeight: 'bold',
        color: '#0f172a',
        textTransform: 'uppercase',
        marginRight: 10,
    },
    separator: {
        flex: 1,
        height: 1,
        backgroundColor: '#cbd5e1',
    },

    // Table
    table: {
        borderRadius: 4,
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: '#e2e8f0',
        marginBottom: 5,
    },
    tableHeaderRow: {
        flexDirection: 'row',
        backgroundColor: '#0f172a', // Dark header
        paddingVertical: 8,
        paddingHorizontal: 6,
    },
    tableRow: {
        flexDirection: 'row',
        borderBottomWidth: 1,
        borderBottomColor: '#f1f5f9',
        paddingVertical: 6,
        paddingHorizontal: 6,
        backgroundColor: '#ffffff',
    },
    tableRowAlt: {
        backgroundColor: '#f8fafc',
    },
    tableHeaderCell: {
        color: 'white',
        fontSize: 8,
        fontWeight: 'bold',
    },
    tableCell: {
        fontSize: 9,
        color: '#334155',
    },

    // Columns
    colDate: { width: '18%' },
    colType: { width: '15%' },
    colClient: { width: '25%' },
    colDetail: { width: '25%' },
    colAmount: { width: '17%', textAlign: 'right' },

    // Badges inside PDF
    badge: {
        fontSize: 7,
        paddingHorizontal: 4,
        paddingVertical: 1,
        borderRadius: 2,
        marginRight: 3,
    },
    badgeCoord: { backgroundColor: '#dbeafe', color: '#1e40af' }, // Blue
    badgeNight: { backgroundColor: '#e0e7ff', color: '#3730a3' }, // Indigo

    // Month Total
    monthTotalRow: {
        flexDirection: 'row',
        backgroundColor: '#f1f5f9',
        paddingVertical: 6,
        paddingHorizontal: 6,
        borderTopWidth: 1.5,
        borderTopColor: '#0f172a',
    },

    footer: {
        position: 'absolute',
        bottom: 20,
        left: 0,
        right: 0,
        textAlign: 'center',
        color: '#94a3b8',
        fontSize: 8,
    }
});

// --- QuickChart Helper ---
const getChartUrl = (type: 'doughnut' | 'bar', data: any[], labels: string[], title: string) => {
    const config = {
        type: type,
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ['#3b82f6', '#93c5fd', '#e2e8f0'], // Blue-500, Blue-300, Slate-200
                borderWidth: 0,
            }]
        },
        options: {
            plugins: {
                // Outlabels plugin creates arrows
                outlabels: {
                    text: '%l %p',
                    color: '#0f172a', // text color
                    stretch: 20, // line length
                    font: {
                        resizable: true,
                        minSize: 10,
                        maxSize: 14
                    }
                },
                legend: { display: false }, // Hide internal legend, use outlabels
                title: { display: false }
            },
            cutoutPercentage: 50, // For donut
        }
    };
    // Need to use JSON.stringify and encodeURIComponent
    const json = JSON.stringify(config);
    return `https://quickchart.io/chart?c=${encodeURIComponent(json)}&w=300&h=200&bkg=transparent`;
};

interface PDFReportProps {
    workLogs: WorkLog[];
    companies: Company[];
    title: string;
    subtitle?: string;
    dateRange: { from: Date; to: Date };
}

export const PDFReport = ({ workLogs, companies, title, subtitle, dateRange }: PDFReportProps) => {

    // --- Logic Reuse (Stats) ---
    const stats = useMemo(() => {
        const income = workLogs.reduce((acc, log) => acc + Number(log.netAmount ?? log.grossAmount ?? log.amount ?? 0), 0);

        let particularHours = 0;
        let tutorialHours = 0;
        const tutorialDates = new Set<string>();
        const particularDates = new Set<string>();
        const allLogDates: Date[] = [];

        workLogs.forEach(log => {
            const logDate = log.date || log.startDate;
            if (logDate) allLogDates.push(new Date(logDate));
            if (log.endDate) allLogDates.push(new Date(log.endDate));

            let days = 1;
            if (log.startDate && log.endDate && log.startDate !== log.endDate) {
                try {
                    const range = eachDayOfInterval({ start: parseISO(log.startDate), end: parseISO(log.endDate) });
                    range.forEach(d => tutorialDates.add(format(d, 'yyyy-MM-dd')));
                    days = range.length;
                } catch (e) {
                    days = 1;
                }
                const dur = Number(log.durationHours ?? log.duration ?? days);
                tutorialHours += dur;
            } else if (logDate) {
                particularDates.add(format(new Date(logDate), 'yyyy-MM-dd'));
                const dur = Number(log.durationHours ?? log.duration ?? 1);
                particularHours += dur;
            }
        });

        // Day counts
        // Fallback: If dateRange is invalid (0/0 issue), use min/max of logs
        let effectiveStart = dateRange?.from;
        let effectiveEnd = dateRange?.to;

        if ((!effectiveStart || !effectiveEnd) && allLogDates.length > 0) {
            effectiveStart = new Date(Math.min(...allLogDates.map(d => d.getTime())));
            effectiveEnd = new Date(Math.max(...allLogDates.map(d => d.getTime())));
        }

        let daysInRange: Date[] = [];
        try {
            if (effectiveStart && effectiveEnd) {
                daysInRange = eachDayOfInterval({ start: effectiveStart, end: effectiveEnd });
            }
        } catch (e) { daysInRange = [] }

        let tutorialDaysCount = 0;
        let particularDaysCount = 0;
        let freeDaysCount = 0;

        daysInRange.forEach(day => {
            const dayStr = format(day, 'yyyy-MM-dd');
            if (tutorialDates.has(dayStr)) tutorialDaysCount++;
            else if (particularDates.has(dayStr)) particularDaysCount++;
            else freeDaysCount++;
        });

        const showTutorials = companies.length === 0 || companies.some(c => c.settings?.features?.tutorials !== false);

        // Chart Data Prep
        const pieDays = {
            data: [tutorialDaysCount, particularDaysCount, freeDaysCount],
            labels: ['Tutorials', 'Particular', 'Libres'],
        };
        // Quick filter for charts (remove 0 values)
        const dayIndices = pieDays.data.map((v, i) => v > 0 ? i : -1).filter(i => i !== -1);
        const dayChartData = {
            data: dayIndices.length > 0 ? dayIndices.map(i => pieDays.data[i]) : [1], // Fallback for empty
            labels: dayIndices.length > 0 ? dayIndices.map(i => pieDays.labels[i]) : ['Sin Datos']
        };

        const pieHours = {
            data: [particularHours, tutorialHours],
            labels: ['Particular', 'Tutorials']
        };
        const hourIndices = pieHours.data.map((v, i) => v > 0 ? i : -1).filter(i => i !== -1);
        const hourChartData = {
            data: hourIndices.length > 0 ? hourIndices.map(i => pieHours.data[i]) : [1],
            labels: hourIndices.length > 0 ? hourIndices.map(i => pieHours.labels[i]) : ['Sin Datos']
        };

        return {
            income,
            totalHours: particularHours + tutorialHours,
            workDays: tutorialDaysCount + particularDaysCount,
            totalDays: daysInRange.length,
            dayChartData,
            hourChartData,
            breakdowns: {
                days: { tutorial: tutorialDaysCount, particular: particularDaysCount, free: freeDaysCount },
                hours: { particular: particularHours, tutorial: tutorialHours }
            }
        };
    }, [workLogs, companies, dateRange]);

    // --- Grouping ---
    const groupedLogs = useMemo(() => {
        const groups = new Map<string, WorkLog[]>();
        const sorted = [...workLogs].sort((a, b) => {
            const dateA = new Date(a.date || a.startDate || a.createdAt);
            const dateB = new Date(b.date || b.startDate || b.createdAt);
            return dateA.getTime() - dateB.getTime();
        });
        sorted.forEach(log => {
            const d = new Date(log.date || log.startDate || log.createdAt);
            const key = format(d, 'MMMM yyyy');
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key)!.push(log);
        });
        return groups;
    }, [workLogs]);

    // Charts URLs
    const hoursChartUrl = getChartUrl('doughnut', stats.hourChartData.data, stats.hourChartData.labels, 'Hours');


    return (
        <Document>
            <Page size="A4" style={styles.page}>

                {/* Header */}
                <View style={styles.headerContainer}>
                    <View style={styles.headerLeft}>
                        <View style={styles.logoBox}>
                            <Text style={styles.logoText}>V</Text>
                        </View>
                        <View>
                            <Text style={styles.appTitle}>VESOTEL</Text>
                            <Text style={styles.appSubtitle}>Informe de Jornadas</Text>
                        </View>
                    </View>
                    <View style={styles.headerRight}>
                        <Text style={styles.reportTitle}>{title}</Text>
                        <Text style={{ fontSize: 9, color: '#94a3b8', fontFamily: 'Helvetica', marginBottom: 2 }}>
                            {dateRange.from && dateRange.to ? `${format(new Date(dateRange.from), "dd/MM/yyyy")} - ${format(new Date(dateRange.to), "dd/MM/yyyy")}` : ''}
                        </Text>
                        <Text style={styles.generatedDate}>{format(new Date(), 'dd/MM/yyyy HH:mm')}</Text>
                    </View>
                </View>

                {/* Summary Section */}
                <Text style={styles.sectionTitle}>Resumen Global</Text>
                <View style={styles.summaryGrid}>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Total Ingresos</Text>
                        <Text style={styles.cardValue}>{formatCurrency(stats.income)}</Text>
                    </View>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Días Trabajados</Text>
                        <Text style={styles.cardValue}>
                            {stats.workDays}
                            <Text style={{ fontSize: 12, color: '#94a3b8', fontWeight: 'normal' }}>/{stats.totalDays}</Text>
                        </Text>
                    </View>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Horas Totales</Text>
                        <Text style={styles.cardValue}>{stats.totalHours.toFixed(0)}h</Text>
                    </View>
                </View>

                {/* Charts Section */}
                <View style={styles.chartSection}>
                    {/* Days Chart - Horizontal Bar (Dashboard Style) */}
                    <View style={[styles.chartContainer, { flex: 1 }]}>
                        <Text style={styles.chartTitle}>Distribución de Días</Text>

                        <View style={{ height: 20 }} />

                        {/* Bar */}
                        <View style={{
                            flexDirection: 'row',
                            height: 24,
                            width: '100%',
                            backgroundColor: '#e2e8f0',
                            borderRadius: 12,
                            overflow: 'hidden',
                        }}>
                            {/* Tutorials (Blue 500) */}
                            {stats.breakdowns.days.tutorial > 0 && (
                                <View style={{
                                    width: `${(stats.breakdowns.days.tutorial / stats.totalDays) * 100}%`,
                                    backgroundColor: '#3b82f6',
                                    height: '100%',
                                    borderRightWidth: 1,
                                    borderRightColor: '#fff'
                                }} />
                            )}
                            {/* Particular (Blue 300) */}
                            {stats.breakdowns.days.particular > 0 && (
                                <View style={{
                                    width: `${(stats.breakdowns.days.particular / stats.totalDays) * 100}%`,
                                    backgroundColor: '#93c5fd',
                                    height: '100%',
                                    borderRightWidth: 1,
                                    borderRightColor: '#fff'
                                }} />
                            )}
                            {/* Free days fill the rest implicitly due to container background color */}
                        </View>

                        {/* Labels/Legend */}
                        <View style={{ flexDirection: 'row', gap: 10, marginTop: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
                                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#3b82f6' }} />
                                <Text style={{ fontSize: 8, color: '#334155' }}>Tut: {stats.breakdowns.days.tutorial}</Text>
                            </View>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
                                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#93c5fd' }} />
                                <Text style={{ fontSize: 8, color: '#334155' }}>Part: {stats.breakdowns.days.particular}</Text>
                            </View>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
                                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#e2e8f0' }} />
                                <Text style={{ fontSize: 8, color: '#334155' }}>Libres: {stats.breakdowns.days.free}</Text>
                            </View>
                        </View>
                    </View>

                    {/* Hours Chart - Keeps Pie/Doughnut to match Dashboard */}
                    <View style={styles.chartContainer}>
                        <Text style={styles.chartTitle}>Distribución de Horas</Text>
                        <Image src={hoursChartUrl} style={styles.chartImage} />
                        <View style={{ flexDirection: 'row', gap: 8, marginTop: 5, flexWrap: 'wrap', justifyContent: 'center' }}>
                            <Text style={{ fontSize: 8, color: '#334155' }}>
                                Part: <Text style={{ fontWeight: 'bold' }}>{stats.breakdowns.hours.particular.toFixed(1)}h</Text>
                            </Text>
                            <Text style={{ fontSize: 8, color: '#334155' }}>
                                Tut: <Text style={{ fontWeight: 'bold' }}>{stats.breakdowns.hours.tutorial.toFixed(1)}h</Text>
                            </Text>
                        </View>
                    </View>
                </View>

                {/* Monthly Tables */}
                {Array.from(groupedLogs.entries()).map(([month, logs]) => (
                    <View key={month} break={false} style={styles.monthContainer}>
                        <View style={styles.monthHeader}>
                            <Text style={styles.monthTitle}>{month}</Text>
                            <View style={styles.separator} />
                        </View>

                        <View style={styles.table}>
                            {/* Table Header */}
                            <View style={styles.tableHeaderRow}>
                                <View style={styles.colDate}><Text style={styles.tableHeaderCell}>Fecha</Text></View>
                                <View style={styles.colType}><Text style={styles.tableHeaderCell}>Tipo</Text></View>
                                <View style={styles.colClient}><Text style={styles.tableHeaderCell}>Cliente</Text></View>
                                <View style={styles.colDetail}><Text style={styles.tableHeaderCell}>Detalles</Text></View>
                                <View style={styles.colAmount}><Text style={styles.tableHeaderCell}>Importe</Text></View>
                            </View>

                            {/* Rows */}
                            {logs.map((log, i) => (
                                <View key={i} style={[styles.tableRow, i % 2 !== 0 ? styles.tableRowAlt : {}]}>
                                    <View style={styles.colDate}>
                                        <Text style={styles.tableCell}>
                                            {log.type === 'tutorial' && log.startDate && log.endDate
                                                ? `${format(new Date(log.startDate), "dd/MM")}-${format(new Date(log.endDate), "dd/MM/yy")}`
                                                : log.date ? format(new Date(log.date), "dd/MM/yy") : "-"}
                                        </Text>
                                        {log.startTime && log.endTime && (
                                            <Text style={[styles.tableCell, { fontSize: 7, color: '#64748b' }]}>
                                                {log.startTime}-{log.endTime}
                                            </Text>
                                        )}
                                    </View>
                                    <View style={styles.colType}>
                                        <Text style={[styles.tableCell, { textTransform: 'capitalize' }]}>{log.type}</Text>
                                    </View>
                                    <View style={styles.colClient}>
                                        <Text style={styles.tableCell}>{log.extraData?.client || log.description || '-'}</Text>
                                    </View>
                                    <View style={[styles.colDetail, { flexDirection: 'row', flexWrap: 'wrap', gap: 2 }]}>
                                        {log.hasCoordination && (
                                            <View style={{ backgroundColor: '#dbeafe', paddingHorizontal: 4, paddingVertical: 1, borderRadius: 2 }}>
                                                <Text style={{ fontSize: 7, color: '#1e40af' }}>Coord</Text>
                                            </View>
                                        )}
                                        {log.hasNight && (
                                            <View style={{ backgroundColor: '#e0e7ff', paddingHorizontal: 4, paddingVertical: 1, borderRadius: 2 }}>
                                                <Text style={{ fontSize: 7, color: '#3730a3' }}>Noct</Text>
                                            </View>
                                        )}
                                    </View>
                                    <View style={styles.colAmount}>
                                        <Text style={[styles.tableCell, { fontWeight: 'bold' }]}>
                                            {formatCurrency(Number(log.netAmount ?? log.grossAmount ?? log.amount ?? 0))}
                                        </Text>
                                    </View>
                                </View>
                            ))}

                            {/* Month Subtotal */}
                            <View style={styles.monthTotalRow}>
                                <View style={{ flex: 1 }}><Text style={[styles.tableCell, { textAlign: 'right', fontWeight: 'bold', textTransform: 'uppercase', marginRight: 10 }]}>Total {month}</Text></View>
                                <View style={styles.colAmount}>
                                    <Text style={[styles.tableCell, { fontWeight: 'bold' }]}>
                                        {formatCurrency(logs.reduce((sum, l) => sum + Number(l.netAmount ?? l.grossAmount ?? l.amount ?? 0), 0))}
                                    </Text>
                                </View>
                            </View>
                        </View>
                    </View>
                ))}

                <Text style={styles.footer} fixed>Reporte Oficial - Ski Vesotel</Text>
            </Page>
        </Document>
    );
};
