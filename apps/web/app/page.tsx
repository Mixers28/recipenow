export default function Home() {
  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-3xl font-bold text-gray-900 mb-4">Welcome to RecipeNow</h2>
        <p className="text-lg text-gray-600 mb-6">
          Convert your recipe photos and screenshots into structured, searchable recipes with complete provenance tracking.
        </p>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="border border-gray-200 rounded-lg p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">📚 Recipe Library</h3>
          <p className="text-gray-600">
            Upload recipe images, review extracted data, and build your digital recipe collection.
          </p>
        </div>

        <div className="border border-gray-200 rounded-lg p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">🥘 Pantry Matching</h3>
          <p className="text-gray-600">
            Maintain your pantry and discover what recipes you can cook with available ingredients.
          </p>
        </div>
      </section>

      <section className="mt-8">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">Getting Started</h3>
        <ul className="space-y-2 text-gray-600">
          <li>✓ Upload a recipe photo or screenshot</li>
          <li>✓ Review and correct extracted fields</li>
          <li>✓ Verify your recipe</li>
          <li>✓ Match recipes to your pantry</li>
        </ul>
      </section>

      <section className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded">
        <p className="text-sm text-blue-900">
          <strong>Status:</strong> RecipeNow V1 is under development. Core features coming soon!
        </p>
      </section>
    </div>
  )
}
