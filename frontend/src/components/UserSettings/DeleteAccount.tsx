import DeleteConfirmation from "./DeleteConfirmation"

const DeleteAccount = () => {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="max-w-2xl">
        <h3 className="text-sm font-semibold text-red-950">Delete account</h3>
        <p className="mt-1 text-sm leading-6 text-red-700/75">
          This permanently removes your saved articles, preferences, and account
          data.
        </p>
      </div>
      <DeleteConfirmation />
    </div>
  )
}

export default DeleteAccount
