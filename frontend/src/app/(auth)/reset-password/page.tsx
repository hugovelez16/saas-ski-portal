"use client"

import { useState, Suspense } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Loader2, KeyRound, CheckCircle2 } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"
import { resetPassword } from "@/lib/api/users"
import { LegalFooter } from "@/components/legal-footer"

function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token")

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!token) {
      setError("Falta el token de seguridad. Por favor, solicita un nuevo enlace.")
      return
    }

    if (password.length < 6) {
      setError("La contraseña debe tener al menos 6 caracteres.")
      return
    }

    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden.")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      await resetPassword({
        token,
        newPassword: password
      })
      setIsSuccess(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || "El token es inválido o ha expirado. Por favor, solicita uno nuevo.")
    } finally {
      setIsLoading(false)
    }
  }

  if (!token && !isSuccess) {
    return (
      <div className="text-center py-6 space-y-4">
        <p className="text-sm text-red-500 font-medium">
          Enlace de recuperación inválido o incompleto.
        </p>
        <Button onClick={() => router.push("/forgot-password")} className="w-full">
          Solicitar nuevo enlace
        </Button>
      </div>
    )
  }

  return (
    <>
      {!isSuccess ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium leading-none">
              Nueva Contraseña
            </label>
            <Input
              id="password"
              type="password"
              placeholder="Mínimo 6 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium leading-none">
              Confirmar Contraseña
            </label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="Repite la contraseña"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          {error && (
            <div className="text-sm text-red-500 font-medium">
              {error}
            </div>
          )}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isLoading ? "Restableciendo..." : "Restablecer Contraseña"}
          </Button>
        </form>
      ) : (
        <div className="text-center py-6 space-y-4">
          <div className="flex justify-center">
            <div className="p-3 bg-green-100 rounded-full text-green-600">
              <CheckCircle2 className="h-10 w-10" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-slate-900">¡Contraseña Restablecida!</h3>
          <p className="text-sm text-muted-foreground">
            Tu contraseña ha sido actualizada correctamente. Ya puedes iniciar sesión con tus nuevas credenciales.
          </p>
          <Button onClick={() => router.push("/login")} className="w-full">
            Iniciar Sesión
          </Button>
        </div>
      )}
    </>
  )
}

export default function ResetPasswordPage() {
  return (
    <div
      className="flex min-h-screen items-center justify-center px-4 bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/login-bg.png')" }}
    >
      <Card className="w-full max-w-md bg-white/95 backdrop-blur-sm shadow-xl border-slate-200">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Image
              src="/logo.webp"
              alt="Vesotel Logo"
              width={80}
              height={80}
              priority
              className="object-contain"
              style={{ width: "auto", height: "auto" }}
            />
          </div>
          <CardTitle className="text-2xl font-bold">Establecer Contraseña</CardTitle>
          <CardDescription>
            Introduce tu nueva contraseña de acceso.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<div className="flex justify-center py-6"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>}>
            <ResetPasswordForm />
          </Suspense>
        </CardContent>
        <CardFooter className="flex flex-col items-center gap-2 text-xs text-muted-foreground">
          <span>Vesotel Work Management © 2026</span>
          <LegalFooter />
        </CardFooter>
      </Card>
    </div>
  )
}
