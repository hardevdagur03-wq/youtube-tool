import { Link } from 'react-router-dom';

export default function ServerError() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center p-8 max-w-md">
        <div className="w-20 h-20 rounded-full bg-red-50 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl font-bold text-red-500">500</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Server error
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          Something went wrong on our end. Please try again later.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Refresh page
          </button>
          <Link
            to="/"
            className="inline-flex items-center px-5 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}
