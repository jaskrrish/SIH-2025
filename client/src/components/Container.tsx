export const Container = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <div className={className || "max-w-5xl  mx-auto my-20 h-screen"}>
        {children}
    </div>
  )
}