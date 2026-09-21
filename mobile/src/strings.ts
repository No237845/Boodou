/** Textes propres à l'app (pas dans app/locales) : navigation et erreurs réseau.
 *  L'espace acteurs est traduit via les clés actor_* / role_* de app/locales, comme /espace sur le web. */

export const S = {
  // Communs, par langue (mos/dyu retombent sur fr).
  common: {
    fr: { back: "Retour", next: "Continuer", cancel: "Annuler", retry: "Réessayer", network: "Pas de connexion. Vérifiez le réseau et réessayez.", server: "Le serveur n'a pas pu traiter la demande.", actors: "Espace acteurs", actors_sub: "Relais, point focal, action sociale, gestionnaire", copy: "Copier le code", copied: "Code copié", search: "Rechercher", changeLang: "Changer de langue", forget: "Effacer et revenir à l'accueil" },
    en: { back: "Back", next: "Continue", cancel: "Cancel", retry: "Retry", network: "No connection. Check the network and try again.", server: "The server could not process the request.", actors: "Staff area", actors_sub: "Relay, focal point, social services, case manager", copy: "Copy the code", copied: "Code copied", search: "Search", changeLang: "Change language", forget: "Clear and go back home" },
    pt: { back: "Voltar", next: "Continuar", cancel: "Cancelar", retry: "Tentar de novo", network: "Sem ligação. Verifique a rede e tente de novo.", server: "O servidor não conseguiu processar o pedido.", actors: "Espaço dos atores", actors_sub: "Relé, ponto focal, ação social, gestor de casos", copy: "Copiar o código", copied: "Código copiado", search: "Pesquisar", changeLang: "Mudar de idioma", forget: "Apagar e voltar ao início" },
    ar: { back: "رجوع", next: "متابعة", cancel: "إلغاء", retry: "إعادة المحاولة", network: "لا يوجد اتصال. تحقق من الشبكة وحاول مرة أخرى.", server: "تعذر على الخادم معالجة الطلب.", actors: "فضاء الجهات الفاعلة", actors_sub: "وسيط، نقطة اتصال، الشؤون الاجتماعية، مدير حالات", copy: "نسخ الرمز", copied: "تم نسخ الرمز", search: "بحث", changeLang: "تغيير اللغة", forget: "مسح والعودة إلى الرئيسية" },
  } as Record<string, Record<string, string>>,
};

export const tc = (lang: string | null, key: string) => (S.common[lang ?? "fr"] ?? S.common.fr)[key] ?? S.common.fr[key] ?? key;
