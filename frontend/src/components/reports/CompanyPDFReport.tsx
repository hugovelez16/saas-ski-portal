/* eslint-disable jsx-a11y/alt-text */
"use client";

import React, { useMemo } from 'react';
import { Page, Text, View, Document, StyleSheet, Image, Font } from '@react-pdf/renderer';
import { format } from 'date-fns';
import { formatCurrency } from '@/lib/utils';
import { Company } from '@/lib/types';

Font.register({
    family: 'Helvetica',
    fonts: [
        { src: 'https://fonts.gstatic.com/s/helveticaneue/v70/1Ptsg8zYS_SKggPNyC0IT4ttDfA.ttf' },
        { src: 'https://fonts.gstatic.com/s/helveticaneue/v70/1Ptsg8zYS_SKggPNyC0IT4ttDfA.ttf', fontWeight: 'bold' }
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
    headerContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#0f172a',
        padding: 20,
        margin: -30,
        marginBottom: 24,
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
    sectionTitle: {
        fontSize: 13,
        fontWeight: 'bold',
        color: '#0f172a',
        borderLeftWidth: 4,
        borderLeftColor: '#0f172a',
        paddingLeft: 8,
        marginBottom: 12,
        marginTop: 6,
    },
    summaryGrid: {
        flexDirection: 'row',
        gap: 8,
        marginBottom: 16,
    },
    card: {
        flex: 1,
        backgroundColor: '#f8fafc',
        borderRadius: 6,
        padding: 10,
        borderWidth: 1,
        borderColor: '#e2e8f0',
    },
    cardTitle: {
        fontSize: 7.5,
        color: '#64748b',
        fontWeight: 'bold',
        textTransform: 'uppercase',
        marginBottom: 4,
    },
    cardValue: {
        fontSize: 15,
        fontWeight: 'bold',
        color: '#0f172a',
    },
    cardSubValue: {
        fontSize: 8,
        color: '#64748b',
        marginTop: 2,
    },
    chartSection: {
        marginBottom: 20,
        alignItems: 'center',
        backgroundColor: '#f8fafc',
        borderRadius: 6,
        padding: 12,
        borderWidth: 1,
        borderColor: '#e2e8f0',
    },
    chartImage: {
        width: 400,
        height: 180,
        objectFit: 'contain',
    },
    table: {
        borderRadius: 4,
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: '#e2e8f0',
        marginBottom: 5,
    },
    tableHeaderRow: {
        flexDirection: 'row',
        backgroundColor: '#0f172a',
        paddingVertical: 7,
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
        fontSize: 8.5,
        color: '#334155',
    },
    colName: { width: '32%' },
    colHours: { width: '16%', textAlign: 'right' },
    colDays: { width: '16%', textAlign: 'right' },
    colGross: { width: '18%', textAlign: 'right' },
    colNet: { width: '18%', textAlign: 'right' },
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

const getEmployeesChartUrl = (labels: string[], data: number[]) => {
    const displayLabels = labels.slice(0, 10);
    const displayData = data.slice(0, 10);

    const config = {
        type: 'bar',
        data: {
            labels: displayLabels,
            datasets: [{
                label: 'Coste Bruto (€)',
                data: displayData,
                backgroundColor: '#3b82f6',
                borderRadius: 4,
            }]
        },
        options: {
            plugins: {
                legend: { display: false },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'top',
                    color: '#64748b',
                    font: { size: 9, weight: 'bold' },
                    formatter: (value: any) => `€${value}`
                }
            },
            scales: {
                y: { beginAtZero: true, grid: { display: true, color: '#e2e8f0' } },
                x: { grid: { display: false } }
            }
        }
    };
    const json = JSON.stringify(config);
    return `https://quickchart.io/chart?c=${encodeURIComponent(json)}&w=500&h=260&bkg=transparent`;
};

export interface EmployeeSummary {
    userId: string;
    name: string;
    totalHours: number;
    totalDays: number;
    totalAmount: number;
    totalGross?: number;
    totalNet?: number;
}

interface CompanyPDFReportProps {
    company: Company;
    employeeStats: EmployeeSummary[];
    title: string;
    startDate: Date;
    endDate: Date;
}

export const CompanyPDFReport = ({ company, employeeStats, title, startDate, endDate }: CompanyPDFReportProps) => {
    const normalizeTaxRate = (val: number | undefined | null) => {
        if (!val || isNaN(val)) return 0;
        const n = Number(val);
        return n > 1 ? n / 100 : n;
    };

    const ssRate = normalizeTaxRate(company?.taxConfig?.social_security);
    const irpfRate = normalizeTaxRate(company?.taxConfig?.irpf_base);
    const totalTaxRate = ssRate + irpfRate;

    const totals = useMemo(() => {
        let hours = 0;
        let days = 0;
        let gross = 0;
        let net = 0;

        employeeStats.forEach(curr => {
            hours += curr.totalHours;
            days += curr.totalDays;

            const currGross = Number(curr.totalGross ?? (totalTaxRate > 0 && totalTaxRate < 1 ? curr.totalAmount / (1 - totalTaxRate) : curr.totalAmount));
            const currNet = Number(curr.totalNet ?? curr.totalAmount);

            gross += currGross;
            net += currNet;
        });

        const ssDeduction = gross * ssRate;
        const irpfDeduction = gross * irpfRate;

        return {
            hours,
            days,
            gross,
            net,
            ssDeduction,
            irpfDeduction,
            totalDeductions: ssDeduction + irpfDeduction
        };
    }, [employeeStats, ssRate, irpfRate, totalTaxRate]);

    const sortedEmployees = [...employeeStats].sort((a, b) => {
        const grossB = b.totalGross ?? b.totalAmount;
        const grossA = a.totalGross ?? a.totalAmount;
        return grossB - grossA;
    });

    const chartUrl = getEmployeesChartUrl(
        sortedEmployees.map(e => e.name.split(' ')[0]),
        sortedEmployees.map(e => Math.round(e.totalGross ?? (totalTaxRate > 0 && totalTaxRate < 1 ? e.totalAmount / (1 - totalTaxRate) : e.totalAmount)))
    );

    return (
        <Document>
            <Page size="A4" style={styles.page}>
                {/* Header */}
                <View style={styles.headerContainer}>
                    <View style={styles.headerLeft}>
                        <View style={styles.logoBox}>
                            <Text style={styles.logoText}>C</Text>
                        </View>
                        <View>
                            <Text style={styles.appTitle}>{company.name}</Text>
                            <Text style={styles.appSubtitle}>Informe Corporativo</Text>
                        </View>
                    </View>
                    <View style={styles.headerRight}>
                        <Text style={styles.reportTitle}>{title}</Text>
                        <Text style={{ fontSize: 9, color: '#94a3b8', fontFamily: 'Helvetica', marginBottom: 2 }}>
                            {startDate && endDate ? `${format(new Date(startDate), "dd/MM/yyyy")} - ${format(new Date(endDate), "dd/MM/yyyy")}` : ''}
                        </Text>
                        <Text style={styles.generatedDate}>Generado: {format(new Date(), 'dd/MM/yyyy HH:mm')}</Text>
                    </View>
                </View>

                {/* Summary Section */}
                <Text style={styles.sectionTitle}>Resumen Financiero y Operativo</Text>
                <View style={styles.summaryGrid}>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Total Bruto</Text>
                        <Text style={styles.cardValue}>{formatCurrency(totals.gross)}</Text>
                        <Text style={styles.cardSubValue}>Base imponible</Text>
                    </View>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Retenciones Estimadas</Text>
                        <Text style={[styles.cardValue, { color: '#dc2626' }]}>-{formatCurrency(totals.totalDeductions)}</Text>
                        <Text style={styles.cardSubValue}>IRPF: {(irpfRate * 100).toFixed(1)}% | SS: {(ssRate * 100).toFixed(1)}%</Text>
                    </View>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Total Neto</Text>
                        <Text style={[styles.cardValue, { color: '#16a34a' }]}>{formatCurrency(totals.net)}</Text>
                        <Text style={styles.cardSubValue}>Percibido estimado</Text>
                    </View>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>Horas Totales</Text>
                        <Text style={styles.cardValue}>{totals.hours.toFixed(0)}h</Text>
                        <Text style={styles.cardSubValue}>{totals.days} jornadas totales</Text>
                    </View>
                </View>

                {/* Chart */}
                <View style={styles.chartSection}>
                    <Text style={{ fontSize: 9, fontWeight: 'bold', marginBottom: 8, color: '#64748b', textTransform: 'uppercase' }}>
                        Top Empleados por Coste Bruto
                    </Text>
                    <Image src={chartUrl} style={styles.chartImage} />
                </View>

                {/* Employees Table */}
                <Text style={styles.sectionTitle}>Detalle Desglosado por Empleado</Text>
                <View style={styles.table}>
                    <View style={styles.tableHeaderRow}>
                        <View style={styles.colName}><Text style={styles.tableHeaderCell}>Empleado</Text></View>
                        <View style={styles.colHours}><Text style={styles.tableHeaderCell}>Horas</Text></View>
                        <View style={styles.colDays}><Text style={styles.tableHeaderCell}>Días</Text></View>
                        <View style={styles.colGross}><Text style={styles.tableHeaderCell}>Total Bruto</Text></View>
                        <View style={styles.colNet}><Text style={styles.tableHeaderCell}>Total Neto</Text></View>
                    </View>

                    {sortedEmployees.map((emp, i) => {
                        const empGross = Number(emp.totalGross ?? (totalTaxRate > 0 && totalTaxRate < 1 ? emp.totalAmount / (1 - totalTaxRate) : emp.totalAmount));
                        const empNet = Number(emp.totalNet ?? emp.totalAmount);

                        return (
                            <View key={emp.userId} style={[styles.tableRow, i % 2 !== 0 ? styles.tableRowAlt : {}]}>
                                <View style={styles.colName}><Text style={[styles.tableCell, { fontWeight: 'bold' }]}>{emp.name}</Text></View>
                                <View style={styles.colHours}><Text style={styles.tableCell}>{emp.totalHours.toFixed(1)}h</Text></View>
                                <View style={styles.colDays}><Text style={styles.tableCell}>{emp.totalDays}</Text></View>
                                <View style={styles.colGross}><Text style={[styles.tableCell, { fontWeight: 'bold' }]}>{formatCurrency(empGross)}</Text></View>
                                <View style={styles.colNet}><Text style={[styles.tableCell, { color: '#16a34a', fontWeight: 'bold' }]}>{formatCurrency(empNet)}</Text></View>
                            </View>
                        );
                    })}

                    {/* Total Row */}
                    <View style={[styles.tableRow, { borderTopWidth: 2, borderTopColor: '#0f172a', backgroundColor: '#f1f5f9' }]}>
                        <View style={styles.colName}><Text style={[styles.tableCell, { fontWeight: 'bold', textTransform: 'uppercase' }]}>TOTAL</Text></View>
                        <View style={styles.colHours}><Text style={[styles.tableCell, { fontWeight: 'bold' }]}>{totals.hours.toFixed(1)}h</Text></View>
                        <View style={styles.colDays}><Text style={[styles.tableCell, { fontWeight: 'bold' }]}>{totals.days}</Text></View>
                        <View style={styles.colGross}><Text style={[styles.tableCell, { fontWeight: 'bold' }]}>{formatCurrency(totals.gross)}</Text></View>
                        <View style={styles.colNet}><Text style={[styles.tableCell, { fontWeight: 'bold', color: '#16a34a' }]}>{formatCurrency(totals.net)}</Text></View>
                    </View>
                </View>

                <Text style={styles.footer} fixed>Portal SaaS - Informe Corporativo Oficial</Text>
            </Page>
        </Document>
    );
};
