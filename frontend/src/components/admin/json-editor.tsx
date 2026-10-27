"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { AlertCircle, CheckCircle2 } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

interface JsonEditorProps {
    initialValue: any
    onSave: (value: any) => void
    label?: string
    description?: string
    rows?: number
}

/**
 * Recorre recursivamente un valor parseado (objetos y arrays) y devuelve la ruta
 * del primer numero no finito (NaN, Infinity, -Infinity), o null si todos son finitos.
 * La raiz se nombra "$". Ejemplo: "$.rates[1].base_rate".
 */
export function findNonFiniteNumber(value: unknown): string | null {
    const walk = (node: unknown, path: string): string | null => {
        if (typeof node === "number") {
            return Number.isFinite(node) ? null : path
        }
        if (Array.isArray(node)) {
            for (let i = 0; i < node.length; i++) {
                const found = walk(node[i], `${path}[${i}]`)
                if (found !== null) return found
            }
            return null
        }
        if (node !== null && typeof node === "object") {
            for (const [key, child] of Object.entries(node)) {
                const found = walk(child, `${path}.${key}`)
                if (found !== null) return found
            }
        }
        return null
    }
    return walk(value, "$")
}

export function JsonEditor({ initialValue, onSave, label, description, rows = 12 }: JsonEditorProps) {
    const [value, setValue] = React.useState(JSON.stringify(initialValue, null, 2))
    const [error, setError] = React.useState<string | null>(null)
    const [valueError, setValueError] = React.useState<string | null>(null)
    const [isValid, setIsValid] = React.useState(true)

    const initialValueString = JSON.stringify(initialValue, null, 2)
    React.useEffect(() => {
        setValue(initialValueString)
    }, [initialValueString])

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newVal = e.target.value
        setValue(newVal)
        setValueError(null)
        try {
            JSON.parse(newVal)
            setError(null)
            setIsValid(true)
        } catch (err: any) {
            setError(err.message)
            setIsValid(false)
        }
    }

    const handleSave = () => {
        let parsed: unknown
        try {
            parsed = JSON.parse(value)
        } catch {
            // La sintaxis invalida ya se muestra en handleChange; no se guarda nada
            return
        }
        // JSON.parse no produce NaN, pero un literal como 1e400 se convierte en Infinity
        const invalidPath = findNonFiniteNumber(parsed)
        if (invalidPath !== null) {
            setValueError(`El valor en ${invalidPath} no es un número finito (NaN o Infinity). Corríjalo antes de guardar.`)
            return
        }
        setValueError(null)
        onSave(parsed)
    }

    return (
        <div className="space-y-4">
            {(label || description) && (
                <div className="space-y-1">
                    {label && <h3 className="text-sm font-semibold">{label}</h3>}
                    {description && <p className="text-xs text-muted-foreground">{description}</p>}
                </div>
            )}

            <div className="relative">
                <Textarea
                    value={value}
                    onChange={handleChange}
                    rows={rows}
                    className={`text-sm bg-slate-950 text-slate-50 border-2 focus-visible:ring-0 ${isValid ? "border-slate-800" : "border-red-500"
                        }`}
                />
                <div className="absolute bottom-2 right-2 flex items-center gap-2">
                    {!isValid && (
                        <span className="text-[10px] text-red-400 bg-red-950/50 px-2 py-0.5 rounded border border-red-900">
                            JSON Inválido
                        </span>
                    )}
                    {isValid && (
                        <span className="text-[10px] text-green-400 bg-green-950/50 px-2 py-0.5 rounded border border-green-900">
                            Sintaxis Correcta
                        </span>
                    )}
                </div>
            </div>

            {error && (
                <Alert variant="destructive" className="py-2">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle className="text-xs">Error de Formato</AlertTitle>
                    <AlertDescription className="text-[10px]">
                        {error}
                    </AlertDescription>
                </Alert>
            )}

            {valueError && (
                <Alert variant="destructive" className="py-2">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle className="text-xs">Valor no válido</AlertTitle>
                    <AlertDescription className="text-[10px]">
                        {valueError}
                    </AlertDescription>
                </Alert>
            )}

            <Button
                onClick={handleSave}
                disabled={!isValid}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
            >
                Guardar Configuración
            </Button>
        </div>
    )
}
