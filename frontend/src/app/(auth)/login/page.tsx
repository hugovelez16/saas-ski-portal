"use client"

import { useState, useEffect } from "react"
import Image from "next/image"
import { useAuth } from "@/context/AuthContext"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Loader2, Terminal } from "lucide-react"
import { useRouter } from "next/navigation"

// Mensaje de error segun el estado devuelto por /verify-2fa
function twoFactorErrorMessage(err: unknown): string {
  const status = (err as { response?: { status?: number } })?.response?.status
  if (status === 429) return "Demasiados intentos. Espera unos minutos antes de volver a probar"
  if (status === 403) return "La verificación ha caducado. Vuelve a iniciar sesión"
  if (status === 503) return "El servicio de verificación no está disponible. Inténtalo más tarde"
  return "Código incorrecto o expirado"
}

export default function LoginPage() {
  const { login, devLogin, verify2FA } = useAuth()
  const router = useRouter()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [twoFactorCode, setTwoFactorCode] = useState("")
  const [showTwoFactor, setShowTwoFactor] = useState(false)
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isDevMode, setIsDevMode] = useState(false)
  const [devEmail, setDevEmail] = useState("admin@vesotel.com")

  // Comprobar si estamos en entorno de desarrollo y auto-iniciar sesion
  useEffect(() => {
    let isMounted = true;
    const checkDevBypass = async () => {
      try {
        const res = await fetch("/api/auth/dev-status");
        if (res.ok) {
          const data = await res.json();
          if (data.dev_bypass && isMounted) {
            setIsDevMode(true);
            if (data.email) setDevEmail(data.email);
            // Bypass automatico en desarrollo
            setIsLoading(true);
            try {
              await devLogin();
            } catch (bypassErr) {
              console.warn("Fallo el bypass automatico de login, esperando accion manual:", bypassErr);
              if (isMounted) setIsLoading(false);
            }
          }
        }
      } catch (err) {
        // En caso de fallo de conexion o produccion
      }
    };

    checkDevBypass();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      if (showTwoFactor) {
        await verify2FA(twoFactorCode);
      } else if (isDevMode && (!email || !password || email === devEmail)) {
        await devLogin();
      } else {
        const result = await login(email, password);
        if (result.requires2FA) {
          setShowTwoFactor(true);
        }
      }
    } catch (err) {
      setError(
        showTwoFactor
          ? twoFactorErrorMessage(err)
          : "Credenciales inválidas, código incorrecto o error de conexión"
      );
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
              className="object-contain" // Use object-contain to ensure it fits nicely
              style={{ width: "auto", height: "auto" }} // Nextjs aspect ratio fix
            />
          </div>
          <CardTitle className="text-2xl font-bold">Clases Vesotel</CardTitle>
          {/* <CardDescription>Management Backoffice</CardDescription> Removed as requested */}
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!showTwoFactor ? (
              <>
                {isDevMode && (
                  <div className="rounded-md bg-blue-50 p-3 text-xs text-blue-700 border border-blue-200 text-center font-medium">
                    Modo desarrollo activo: Acceso directo como {devEmail}
                  </div>
                )}
                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                    Email
                  </label>
                  <Input
                    id="email"
                    type="email"
                    placeholder={isDevMode ? devEmail : ""}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required={!isDevMode}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <label htmlFor="password" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                      Password
                    </label>
                    <Button 
                      type="button" 
                      variant="link" 
                      className="px-0 h-auto text-xs" 
                      onClick={() => router.push("/forgot-password")}
                    >
                      Forgot password?
                    </Button>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder={isDevMode ? "••••••••" : ""}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required={!isDevMode}
                  />
                </div>
              </>
            ) : (
              <div className="space-y-2">
                <div className="text-sm text-center mb-4 text-muted-foreground">
                  Introduce el código de 6 dígitos de tu aplicación de autenticación.
                </div>
                <label htmlFor="2fa" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  Código de Verificación
                </label>
                <div className="flex justify-center gap-2">
                  {Array.from({ length: 6 }).map((_, index) => (
                    <Input
                      key={index}
                      id={`otp-${index}`}
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={1}
                      value={twoFactorCode[index] || ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (!/^\d*$/.test(val)) return; // Only allow digits

                        const newCode = twoFactorCode.split("");
                        newCode[index] = val;
                        const newCodeStr = newCode.join("");
                        setTwoFactorCode(newCodeStr);

                        // Focus next input or submit
                        if (val && index < 5) {
                          const nextInput = document.getElementById(`otp-${index + 1}`);
                          nextInput?.focus();
                        } else if (val && index === 5 && newCodeStr.length === 6) {
                          setIsLoading(true);
                          // Small delay to allow state update? passed directly
                          verify2FA(newCodeStr)
                            .catch((err) => {
                              setError(twoFactorErrorMessage(err));
                              setTwoFactorCode("");
                              setIsLoading(false);
                            });
                        }
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Backspace" && !twoFactorCode[index] && index > 0) {
                          const prevInput = document.getElementById(`otp-${index - 1}`);
                          prevInput?.focus();
                          // Delete prev char?
                          const newCode = twoFactorCode.split("");
                          newCode[index - 1] = "";
                          setTwoFactorCode(newCode.join(""));
                        }
                      }}
                      className="w-12 h-12 text-center text-xl"
                      required={index === 0} // Only first required implicitly? No, validation on submit
                    />
                  ))}
                </div>

              </div>
            )}
            {error && (
              <div className="text-sm text-red-500 font-medium">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLoading ? "Signing in..." : isDevMode ? "Entrar como Administrador (Dev)" : "Sign In"}
            </Button>
            {/* Request Access Button */}
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="link" className="w-full text-xs text-muted-foreground mt-2">
                  Request Access
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Request Access</DialogTitle>
                  <DialogDescription>
                    Please contact the administrator to request access to the platform.
                    <br /><br />
                    Email: hugo@vesotel.com
                  </DialogDescription>
                </DialogHeader>
              </DialogContent>
            </Dialog>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center text-xs text-muted-foreground">
          Vesotel Work Management © 2026
        </CardFooter>
      </Card>
    </div>
  )
}
