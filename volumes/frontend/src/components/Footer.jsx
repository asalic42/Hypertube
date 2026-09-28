const AUTHORS = ["aciezadl", "aducobu", "asalic", "ldoyen"];

function Footer() {
  return (
    <footer className="w-full bg-gray-900 px-4 pt-4 pb-[max(1rem,env(safe-area-inset-bottom))] text-center text-gray-300">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-center gap-y-1 text-xs sm:flex-row sm:gap-x-3 sm:text-sm">
        <p className="font-medium text-white">© 2026 Hypertube</p>
        <p aria-hidden="true" className="hidden sm:block">·</p>
        <ul className="flex flex-wrap justify-center gap-x-3 gap-y-1">
          {AUTHORS.map((author) => (
            <li key={author}>{author}</li>
          ))}
        </ul>
      </div>
    </footer>
  );
}

export default Footer;
