const TASKS = {
  // Existing tasks...

  createCourse: {
    description: 'Create new course from CLI with token authentication',
    async exec() {
      // Implement token validation and DB creation
    }
  },

  updateCourse: {
    description: 'Edit existing course in database',
    exec(courseId, changes) {
      // Token-verified update
    }
  },

  listCourses: {
    description: 'List all courses from DB',
    exec() {
      // Fetch courses with token check
    }
  }
};export default TASKS;
