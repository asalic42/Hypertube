// Checks a chosen profile picture before any upload, with the same limits as
// the users service. The file is also decoded, so a corrupt or renamed file is
// refused here rather than by the server once the form is submitted.

export const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const AVATAR_MAX_BYTES = 5 * 1024 * 1024;

export const BAD_TYPE = "Use a JPEG, PNG or WebP image.";
export const TOO_LARGE = "The picture is too large: choose an image of 5 MB or less.";
export const UNREADABLE = "This file could not be read as an image.";

function decodes(file) {
    return new Promise((resolve) => {
        const url = URL.createObjectURL(file);
        const image = new Image();
        image.onload = () => { URL.revokeObjectURL(url); resolve(true); };
        image.onerror = () => { URL.revokeObjectURL(url); resolve(false); };
        image.src = url;
    });
}

/** The problem with the file, as a { title, description } pair of sentences, or null when it is fine. */
export async function avatarFileProblem(file) {
    if (!AVATAR_TYPES.includes(file.type)) return { title: "Unsupported picture", description: BAD_TYPE };
    if (file.size > AVATAR_MAX_BYTES) return { title: "Picture too large", description: TOO_LARGE };
    if (!(await decodes(file))) return { title: "Unsupported picture", description: UNREADABLE };
    return null;
}
