import GoldenSphere from './components/dashboard/GoldenSphere'

export default function SpherePrototype() {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: '#000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <GoldenSphere size={620} />
    </div>
  )
}
