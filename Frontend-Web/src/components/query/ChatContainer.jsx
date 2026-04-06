export default function ChatContainer({ children, className = "", ...props }) {
  return (
    <section
      className={`mx-auto flex w-full max-w-3xl flex-1 flex-col ${className}`}
      {...props}
    >
      {children}
    </section>
  );
}
