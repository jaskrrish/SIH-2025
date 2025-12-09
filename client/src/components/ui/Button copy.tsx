export const Button = ({ children }: { children: React.ReactNode }) => {
  return (
    <button className="relative bg-accent px-4 py-2 rounded-xl cursor-pointer overflow-hidden  border border-accent/80 text-white font-semibold shadow-lg hover:bg-accent/90 transition-colors">
      {children}
      <div className="absolute bottom-0 inset-x-0 w-full h-px bg-gradient-to-r from-transparent via-white/50 to-transparent"></div>
    </button>
  );
};
