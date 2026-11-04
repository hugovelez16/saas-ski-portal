"use client"

import { useState } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Loader2, ArrowLeft, MailCheck } from "lucide-react"
import { useRouter } from "next/navigation"
import { forgotPassword } from "@/lib/api/users"
import { LegalFooter } from "@/components/legal-footer"

export default function ForgotPasswordPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      await forgotPassword(email)
      setIsSubmitted(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Ha ocurrido un error al procesar tu solicitud.")
    } finally {
      setIsLoading(false)
    }
  }

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
          <CardTitle className="text-2xl font-bold">Recuperar Contraseña</CardTitle>
          <CardDescription>
            Introduce tu correo electrónico y te enviaremos un enlace para restablecer tu contraseña.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!isSubmitted ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium leading-none">
                  Correo Electrónico
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="ejemplo@vesotel.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
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
                {isLoading ? "Enviando..." : "Enviar enlace de recuperación"}
              </Button>
            </form>
          ) : (
            <div className="text-center py-6 space-y-4">
              <div className="flex justify-center">
                <div className="p-3 bg-green-100 rounded-full text-green-600">
                  <MailCheck className="h-10 w-10" />
                </div>
              </div>
              <h3 className="text-lg font-semibold text-slate-900">Enlace Enviado</h3>
              <p className="text-sm text-muted-foreground">
                Si el correo electrónico <strong>{email}</strong> está registrado, habrás recibido un enlace para restablecer tu contraseña en unos minutos.
              </p>
            </div>
          )}
        </CardContent>
        <CardFooter className="flex flex-col items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/login")}
            className="text-xs text-muted-foreground gap-2 hover:bg-slate-100"
          >
            <ArrowLeft className="h-3 w-3" /> Volver al Login
          </Button>
          <LegalFooter />
        </CardFooter>
      </Card>
    </div>
  )
}
