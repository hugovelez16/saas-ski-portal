"use client";

import { UserProfile } from "@/lib/types";

interface NotificationsSectionProps {
    user: UserProfile;
}

// El aviso de "empresa por defecto" se retiro: la empresa activa viene del token.
export function NotificationsSection(_props: NotificationsSectionProps) {
    return null;
}
