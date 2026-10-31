"use client";

import { useEffect, useState, type ChangeEvent } from "react";
import {
    CONTACT_EMAIL,
    CONTACT_SUBJECT,
    EMPTY_CONTACT,
    PLAN_CHOICES,
    SELECT_PLAN_EVENT,
    buildContactMessage,
    buildMailtoUrl,
    buildWhatsAppUrl,
    validateContact,
    type ContactData,
    type ContactErrors,
    type PlanChoice,
} from "@/lib/landing-contact";

type FieldKey = keyof ContactData;

// Orden en que se enfoca el primer campo con error.
const FIELD_ORDER: readonly FieldKey[] = ["school", "monitors", "plan", "contactName", "email"];

const controlBase =
    "min-h-11 w-full rounded-[10px] border bg-white px-3.5 text-base text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600";

const inputId = (key: FieldKey) => `contact-${key}`;
const errorId = (key: FieldKey) => `contact-${key}-error`;

function controlClass(errors: ContactErrors, key: FieldKey) {
    return `${controlBase} ${errors[key] ? "border-red-500" : "border-slate-300"}`;
}

function a11yProps(errors: ContactErrors, key: FieldKey) {
    const hasError = Boolean(errors[key]);
    return {
        id: inputId(key),
        "aria-required": true,
        "aria-invalid": hasError ? true : undefined,
        "aria-describedby": hasError ? errorId(key) : undefined,
    } as const;
}

function FieldError({ errors, fieldKey }: { errors: ContactErrors; fieldKey: FieldKey }) {
    const message = errors[fieldKey];
    if (!message) return null;
    return (
        <p id={errorId(fieldKey)} role="alert" className="text-sm text-red-600">
            {message}
        </p>
    );
}

export function ContactForm() {
    const [data, setData] = useState<ContactData>(EMPTY_CONTACT);
    const [errors, setErrors] = useState<ContactErrors>({});

    // Preseleccion de plan desde las tarjetas y la calculadora.
    useEffect(() => {
        const handler = (e: Event) => {
            const plan = (e as CustomEvent<PlanChoice>).detail;
            if (PLAN_CHOICES.some((choice) => choice.value === plan)) {
                setData((d) => ({ ...d, plan }));
            }
        };
        window.addEventListener(SELECT_PLAN_EVENT, handler);
        return () => window.removeEventListener(SELECT_PLAN_EVENT, handler);
    }, []);

    const handleChange = (key: FieldKey) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const value = e.target.value;
        setData((d) => ({ ...d, [key]: value }));
        setErrors((prev) => {
            if (!prev[key]) return prev;
            const next = { ...prev };
            delete next[key];
            return next;
        });
    };

    // Valida; si hay errores enfoca el primero y no abre nada. Si es valido, ejecuta la accion de envio.
    const handleSend = (send: () => void) => {
        const found = validateContact(data);
        setErrors(found);
        const firstInvalid = FIELD_ORDER.find((key) => found[key]);
        if (firstInvalid) {
            document.getElementById(inputId(firstInvalid))?.focus();
            return;
        }
        send();
    };

    const sendWhatsApp = () => {
        handleSend(() => {
            window.open(buildWhatsAppUrl(buildContactMessage(data)), "_blank", "noopener,noreferrer");
        });
    };

    const sendMail = () => {
        handleSend(() => {
            window.open(buildMailtoUrl(CONTACT_SUBJECT, buildContactMessage(data)), "_self");
        });
    };

    return (
        <form
            noValidate
            onSubmit={(e) => e.preventDefault()}
            className="flex flex-col gap-5 rounded-2xl bg-white p-6 text-slate-900 sm:p-8"
        >
            <p className="text-sm text-slate-500">Todos los campos son obligatorios.</p>

            <div className="flex flex-col gap-1.5">
                <label htmlFor={inputId("school")} className="text-sm font-semibold">
                    Nombre de la escuela
                </label>
                <input
                    {...a11yProps(errors, "school")}
                    type="text"
                    autoComplete="organization"
                    value={data.school}
                    onChange={handleChange("school")}
                    className={controlClass(errors, "school")}
                />
                <FieldError errors={errors} fieldKey="school" />
            </div>

            <div className="flex flex-col gap-1.5">
                <label htmlFor={inputId("monitors")} className="text-sm font-semibold">
                    Número aproximado de monitores
                </label>
                <input
                    {...a11yProps(errors, "monitors")}
                    type="text"
                    inputMode="numeric"
                    value={data.monitors}
                    onChange={handleChange("monitors")}
                    className={controlClass(errors, "monitors")}
                />
                <FieldError errors={errors} fieldKey="monitors" />
            </div>

            <div className="flex flex-col gap-1.5">
                <label htmlFor={inputId("plan")} className="text-sm font-semibold">
                    Plan que te interesa
                </label>
                <select
                    {...a11yProps(errors, "plan")}
                    value={data.plan}
                    onChange={handleChange("plan")}
                    className={controlClass(errors, "plan")}
                >
                    {PLAN_CHOICES.map((choice) => (
                        <option key={choice.value} value={choice.value}>
                            {choice.label}
                        </option>
                    ))}
                </select>
                <FieldError errors={errors} fieldKey="plan" />
            </div>

            <div className="flex flex-col gap-1.5">
                <label htmlFor={inputId("contactName")} className="text-sm font-semibold">
                    Nombre de contacto
                </label>
                <input
                    {...a11yProps(errors, "contactName")}
                    type="text"
                    autoComplete="name"
                    value={data.contactName}
                    onChange={handleChange("contactName")}
                    className={controlClass(errors, "contactName")}
                />
                <FieldError errors={errors} fieldKey="contactName" />
            </div>

            <div className="flex flex-col gap-1.5">
                <label htmlFor={inputId("email")} className="text-sm font-semibold">
                    Correo electrónico
                </label>
                <input
                    {...a11yProps(errors, "email")}
                    type="email"
                    autoComplete="email"
                    value={data.email}
                    onChange={handleChange("email")}
                    className={controlClass(errors, "email")}
                />
                <FieldError errors={errors} fieldKey="email" />
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
                <button
                    type="button"
                    onClick={sendWhatsApp}
                    className="min-h-11 w-full rounded-[10px] bg-emerald-700 px-5 py-3 font-semibold text-white hover:bg-emerald-800 sm:w-auto"
                >
                    Enviar por WhatsApp
                </button>
                <button
                    type="button"
                    onClick={sendMail}
                    className="min-h-11 w-full rounded-[10px] border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-900 hover:bg-slate-50 sm:w-auto"
                >
                    Enviar por correo
                </button>
            </div>

            <p className="text-sm text-slate-500">
                No guardamos nada en esta página: al pulsar, se abre WhatsApp o tu correo con el mensaje ya escrito.
            </p>
            <p className="text-sm text-slate-500">
                También puedes escribir a <span className="select-all font-semibold">{CONTACT_EMAIL}</span>
            </p>
        </form>
    );
}
